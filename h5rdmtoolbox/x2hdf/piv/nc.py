import logging
import os
import pathlib
import re
from typing import Tuple, Union, Dict

import numpy as np
import xarray as xr

from .utils import is_time
from ...conventions import StandardizedNameTable

try:
    from scipy.interpolate import LinearNDInterpolator
    from scipy.spatial import Delaunay
except ImportError:
    raise ImportError('Package scipy is not installed. Either install it '
                      'separately or install the repository with pip install h5RDMtolbox [piv]')
try:
    from netCDF4 import Dataset as ncDataset
except ImportError:
    raise ImportError('Package netCDF4 is not installed. Either install it '
                      'separately or install the repository with pip install h5RDMtolbox [piv]')
logger = logging.getLogger('x2hdf')


def _process_pivview_root_attributes(root_attrs):
    """Create new or renames or deletes dictionary entries"""
    root_attrs['recording_date'] = root_attrs['creation_date']

    del root_attrs['creation_date']
    if 'filename' in root_attrs:
        del root_attrs['filename']
    if 'image_bkgd_file' in root_attrs:
        del root_attrs['image_bkgd_file']  # should be dataset!
    if 'image_bkgd2_file' in root_attrs:
        del root_attrs['image_bkgd2_file']  # should be dataset!
    if 'image_mask_file' in root_attrs:
        del root_attrs['image_mask_file']  # should be dataset or can always be reconstructed from piv_flags!
    return root_attrs


def process_pivview_nc_data(nc_file: pathlib.Path, interpolate: bool,
                            apply_mask: bool, masking: str,
                            timestep: float, time_unit: str = 's',
                            z_source: str = 'coord_min',
                            compute_dwdz: bool = False,
                            build_coord_datasets: bool = True,
                            standardized_name_table: Union[StandardizedNameTable, None] = None) -> Tuple[
    Dict, Dict, Dict]:
    """
    Reads data and attributes from netCDF file. Results are stored in dictionary. Interpolation
    to fill "holes"/masked areas is applied if asked. Data arrays x, y, z and time are created.
    Array shape is changed from (1, ny, nx) and (1, ny, nx, nv) to (ny, nx). Thus new variables are
    created:
        velocity (1, ny, nx, 2[3]) --> u (ny, nx), v (ny, nx) [, w (ny, nx)]
        piv_data (1, ny, nx, 2[3]) --> dx (ny, nx), dy (ny, nx) [, dz (ny, nx)]
        piv_peak1 (1, ny, nx, 3) --> piv_peak1_dx (ny, nx), piv_peak1_dy (ny, nx), piv_peak1_corr
        piv_peak2 (see above)
        piv_peak3 (see above)

    Parameters
    ----------
    nc_file : Path
        path to nc file
    interpolate : bool, optional=True
        Use space interpolation (linear) in each timeframe to patch holes
        left out after masking.
    apply_mask : bool, optional=True
        Apply the mask to blank masked values to nan which is only useful with
        interpolation. Defaults to True.
    masking : str, optional='sepeaks'
        Masking mode from piv flags. Can be slack or sepeaks or strict.
            strict: only uses true good values
            slack: also uses interpolated values.
            sepeaks: uses strict and second corr. peaks.
        The default is 'sepeaks'.
    timestep : float
        Time step in [s] relative to measurement start. If astropy-quantity
        is passed, unit is taken from there.
    time_unit : str, optional='s'
        unit taken for time if time was not of type astropy.quantity.
    z_source: str or tuple, optional='coord_min'
        The z-location can be specified manually by passing a astropy quantity
        or a list/tuple in form  (value: float, unit: str).
        It also possible to detect the z-location from the nc-file (experience shows
        that this was not always correctly set by the experimenter...). Alternative,
        the z-location is tried to determined by the file name.
        Automatic detection from nc file can be used scanning one of the following
        attributes which then are to be passed as string for this parameter:
            * 'coord_min'
            * 'coord_max'
            * 'origin_offset'
            * 'file'
    compute_dwdz: bool, optional=False
        Computing the out-of-plane gradient dwdz evaluating the continuity equation.
        Only valid for incompressible flows!!!
    build_coord_datasets: bool, optional=True
        Whether to generate x,y,z,t datasets. For single snapshot HDF built this should
        be set True. For plane or case generation except the first snapshot, this can be
        set to False and thus reduce computation time.

    Returns
    -------
    piv_data_array_dict : dict
        Dictionary containing the arrays
    ncRootAttributes : dict
        Attribute dictionary of root variables
    variable_attributes : dict
        Attribute dictionary of dataset variables

    Notes
    -----
    Credits to M. Elfner (ITS, Karlsruhe Institute of Technology)

    """

    # TODO get rid of ncRootAttributes

    def _build_meshgrid_xy(coord_min, coord_max, width, height):
        """generates coord meshgrid from velocity attribute stating min/max of coordinates x, y"""
        _x = np.linspace(coord_min[0], coord_max[0], width)
        _y = np.linspace(coord_min[1], coord_max[1], height)
        return np.meshgrid(_x, _y)

    # read netCDF4 data (array, root attributes and variable attributes)
    with ncDataset(nc_file, "r") as nc_rootgrp:
        dims = nc_rootgrp.dimensions
        d, h, w, vd = (dims['data_array_depth'].size, dims['data_array_height'].size,
                       dims['data_array_width'].size, dims['vec_dims'].size)

        if d > 1:
            logger.critical('File with depth not implemented')
            raise NotImplementedError('File with depth not implemented')

        root_attributes = {key: nc_rootgrp.getncattr(key) for key in
                           ('file_content', 'creation_date', 'software')}
        ncRootAttributes = _process_pivview_root_attributes(
            {attr: nc_rootgrp.getncattr(attr) for attr in nc_rootgrp.ncattrs()})

        variable_attributes = dict()

        # Variable information.
        nc_data_array_dict = nc_rootgrp.variables

        if ncRootAttributes['outlier_interpolate'] and masking != 'slack':
            logger.debug('Outlier masking does not conform with pivview settings in nc '
                         f'(outlier_interpolate={ncRootAttributes["outlier_interpolate"]} vs {masking}) - '
                         f'averages might differ')
        elif ncRootAttributes['outlier_try_other_peak'] and masking != 'sepeaks':
            logger.debug('Outlier masking does not conform with pivview settings in nc '
                         f'(outlier_interpolate={ncRootAttributes["outlier_interpolate"]} vs {masking}) - '
                         f'averages might differ')

        # processed
        piv_data_array_dict = dict()

        for v in nc_data_array_dict.keys():
            variable_attributes[v] = {key: nc_data_array_dict[v].getncattr(key) for key in
                                      nc_data_array_dict[v].ncattrs()}

        try:
            pivflags = np.asarray(nc_data_array_dict['piv_flags'])[0, ...]  # dtype int8

            if masking == 'strict':  # Use only true valid values
                # only keeps "active" ones (flag=1)
                mask = pivflags == 1
                masking_meaning = 'only true valid values are taken'
            elif masking == 'sepeaks':  # True valid and other peaks
                # only keeps flag=65 and flag=1
                # 1: active
                # 64: replaced
                # 65: active+replaced (by other peaks)
                mask = np.logical_or(pivflags == 1, pivflags == 65)
                masking_meaning = 'only true valid and other peaks values are taken'
            elif masking == 'slack':  # Anything that is valid after other peaks, interpolation...
                # everything but 10 (masked+disabled)
                mask = pivflags != 10
                masking_meaning = 'anything that is valid after other peaks are taken'
            elif masking == 'none' or masking is None:
                mask = np.ones_like(pivflags).astype(bool)
                masking_meaning = 'everything is considered valid'
            else:
                logger.critical('Invalid masking mode')
                raise RuntimeError(f'Invalid masking mode: {masking}')

            ncRootAttributes['h5piv_masking'] = masking
            ncRootAttributes['h5piv_mask'] = True

        except KeyError:
            logger.warning(f'PIV flags not found, masking disabled, mode {masking} not used')
            mask = np.ones((h, w)).astype(bool)
            ncRootAttributes['h5piv_mask'] = False

        piv_data_array_dict['valid'] = mask
        variable_attributes['valid'] = {'units': '',
                                        'long_name': 'valid data based on user '
                                                     'input during nc-to-hdf conversion. '
                                                     f'{masking} was used, which means '
                                                     f'"{masking_meaning}".'}

        piv_data_array_dict['piv_flags'] = pivflags

        for k, v in nc_data_array_dict.items():
            if k == 'piv_data':
                for i, name in zip(range(v.shape[-1]), ('dx', 'dy', 'dz')):
                    data = v[0, :, :, i]
                    if apply_mask:
                        data[~mask] = np.nan
                    piv_data_array_dict[name] = data
                    variable_attributes[name] = {'units': 'pixel'}
            elif k == 'velocity':
                for i, name in zip(range(v.shape[-1]), ('u', 'v', 'w')):
                    data = v[0, :, :, i]
                    if apply_mask:
                        data[~mask] = np.nan
                    piv_data_array_dict[name] = data
                    variable_attributes[name] = {'units': variable_attributes['velocity']['units']}
            elif k == 'piv_flags':
                variable_attributes[k].update({'units': ''})
                continue  # We take the flags from above to save computation time
            elif k in ('piv_peak1', 'piv_peak2', 'piv_peak3'):
                for i, suffix, units in zip(range(v.shape[-1]),
                                            ('_dx', '_dy', '_corr'),
                                            ('pixel', 'pixel', '')):
                    data = v[0, :, :, i]
                    if apply_mask:
                        data[~mask] = np.nan
                    name = f'{k}{suffix}'
                    piv_data_array_dict[name] = data
                    variable_attributes[name] = {'units': units}
            else:
                data = v[0, ...]
                if apply_mask:
                    if data.dtype not in (np.int8, np.int16, np.int32):
                        data[~mask] = np.nan
                piv_data_array_dict[k] = data
                if k == 'piv_correlation_coeff':
                    variable_attributes[k].update({'units': ''})
                elif k == 'piv_snr_data':
                    variable_attributes[k].update({'units': ''})
                elif k == 'piv_3c_residuals':
                    variable_attributes[k].update({'units': '',
                                                   'long_name': 'least square residual for z_velocity',
                                                   'comment': 'Residuals from least-squares fit to determined '
                                                              'out-of-plane component. It is a measure of quality of '
                                                              'the vector reconstruction and should be lower than 0.5 '
                                                              'pixel'})
                elif 'velocity gradient' in variable_attributes[k]['long_name']:
                    variable_attributes[k].update({'units': f"1/{variable_attributes['velocity']['units'][-1]}"})

        if interpolate:
            # While there exist some base functions assuming reg. grids and / or
            # using splines, a true interpolation considering distances is the way
            # to go here. Any other, faster methods rely on splines which are not
            # bounded!
            # Qhull on location with valid data
            if 'x' and 'y' not in piv_data_array_dict.keys():
                xm, ym = _build_meshgrid_xy(nc_data_array_dict['velocity'].coord_min,
                                            nc_data_array_dict['velocity'].coord_max,
                                            w, h)
            xv = xm.ravel()[mask.ravel()]
            yv = ym.ravel()[mask.ravel()]
            xi = xm.ravel()[~mask.ravel()]
            yi = ym.ravel()[~mask.ravel()]
            tri = Delaunay(np.stack((xv, yv)).T)

            # interpolate, create and evaluate, write
            for k, v in piv_data_array_dict.items():

                # skip iteration if k in the following variables
                if k in ('x', 'y', 'valid', 'piv_flags'):
                    continue

                data = v.copy()
                interpolator = LinearNDInterpolator(tri, data.ravel()[mask.ravel()])
                interpolated_result = interpolator(xi, yi)
                data[~mask] = interpolated_result

                piv_data_array_dict[k] = data

        # Check if source for w gradients is available, if so compute.
        # CAREFUL with indexing: Meshgrids are YX indexed by default!
        if 'w' in piv_data_array_dict or build_coord_datasets:
            fr, to = nc_data_array_dict['velocity'].coord_min, nc_data_array_dict['velocity'].coord_max
            px_fr, px_to = nc_data_array_dict['piv_data'].coord_min, nc_data_array_dict['piv_data'].coord_max

        if 'w' in piv_data_array_dict:

            # grid spacing is assumed to be homogeneous - is the case for PIV measurements!
            dx, dy = (to[:2] - fr[:2]) / (np.array([w, h]) - 1)

            dwdx = np.gradient(piv_data_array_dict['w'], dx, axis=1)
            dwdy = np.gradient(piv_data_array_dict['w'], dy, axis=0)

            piv_data_array_dict['dwdx'] = dwdx
            piv_data_array_dict['dwdy'] = dwdy

            _gradient_unit = f"1/{variable_attributes['velocity']['units'][-1]}"
            variable_attributes['dwdx'] = {'units': _gradient_unit}
            variable_attributes['dwdy'] = {'units': _gradient_unit}

            if compute_dwdz:
                if 'dudx' in piv_data_array_dict.keys() and 'dvdy' in piv_data_array_dict.keys():
                    logger.info("Gradient \"dwdz\" calculated from continuity equation assuming incompressible flow!")
                    piv_data_array_dict['dwdz'] = -piv_data_array_dict['dudx'] - piv_data_array_dict['dvdy']
                    variable_attributes['dwdz'] = {'units': _gradient_unit}
                else:
                    logger.error(
                        "Could not compute dwdz based on continuity as dudx and dvdy are missing. Continuing ...")

        piv_data_array_dict['time'] = timestep
        variable_attributes['time'] = {'long_name': 'Recording time since start.',
                                       'units': time_unit}
        if not is_time(variable_attributes['time']['units']):
            raise AttributeError(f'Time unit is incorrect: {variable_attributes["t"]["unit"]}')

        # x,y,z,t are not part of PIVview netCDF variables
        if build_coord_datasets:  # can speed up computation when plane or case HDF files are generated
            # the velocity dataset has the attribute coord_min and coord_max from which the coordinates can be derived:
            piv_data_array_dict['x'] = np.linspace(fr[0], to[0], w)
            piv_data_array_dict['y'] = np.linspace(fr[1], to[1], h)
            variable_attributes['x'] = {'units': ncRootAttributes['length_conversion_units']}
            variable_attributes['y'] = {'units': ncRootAttributes['length_conversion_units']}
            piv_data_array_dict['ix'] = np.linspace(px_fr[0], px_to[0], w).astype(int)
            piv_data_array_dict['iy'] = np.linspace(px_fr[1], px_to[1], h).astype(int)
            variable_attributes['ix'] = {'long_name': 'pixel x-location of vector',
                                         'standard_name': 'x_pixel_coordinate',
                                         'units': 'pixel'}
            variable_attributes['iy'] = {'long_name': 'pixel y-location of vector',
                                         'standard_name': 'y_pixel_coordinate',
                                         'units': 'pixel'}

            # Z position information
            z_unit = ncRootAttributes['length_conversion_units']  # default unit of z comes from file
            if isinstance(z_source, str):
                if z_source == 'coord_min':
                    z = fr[2]
                elif z_source == 'coord_max':
                    z = to[2]
                elif z_source == 'origin_offset':
                    z = ncRootAttributes['origin_offset_z']
                elif z_source == 'file':
                    try:
                        z = float(
                            re.findall(
                                r'([-+\d].*)', os.path.split(os.path.dirname(nc_file))[-1])[0])
                    except Exception as e:
                        logger.warning(f'Z level detection failed due to: {e}')
                        z = 0
            elif isinstance(z_source, xr.DataArray):
                z = z_source.values
                z_unit = z_source.units
            elif isinstance(z_source, tuple) or isinstance(z_source, list):
                z, z_unit = z_source
            else:
                logger.warning('Z level detection failed: Invalid mode')
                z = 0

            piv_data_array_dict['z'] = z
            variable_attributes['z'] = {'units': z_unit}

        # correct shape if needed to (nz, nt, ny, nx) or (nz, nt, ny, nx, nv) respectively
        for k, v in piv_data_array_dict.items():
            if k not in ('x', 'y', 'z', 'time'):
                if v.ndim > 2:  # single var dataset or vector dataset
                    piv_data_array_dict[k] = v[0, ...]
                else:  # mask, coordinates
                    piv_data_array_dict[k] = v

    # standardized naming:
    if standardized_name_table is not None:
        if standardized_name_table.has_translation_dictionary:
            for k, v in variable_attributes.items():
                if standardized_name_table:
                    sn = standardized_name_table.translate(k, 'pivview')
                    if sn:
                        v['standard_name'] = sn

    return piv_data_array_dict, root_attributes, variable_attributes
