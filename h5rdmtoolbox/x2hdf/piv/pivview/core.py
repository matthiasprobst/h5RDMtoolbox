import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Union, Dict

import h5py

from .. import config
from .._config import read_yaml_file, check_yaml_file
from ..statistics import running_std, running_mean
from .... import conventions
from ...._version import __version__
from ....conventions.data import DataSourceType, DataSource
from ....conventions.translations import pivview_to_standardnames_dict

logger = logging.getLogger('x2hdf')

# use this name to store pivview parameters/config in HDF file (for snapshot and plane, an attribute name at root level
# is created. A case file gets a group called as defined below and then creates "plane00", "plane01", ... attributes.
PIV_PARAMTER_HDF_NAME = 'piv_parameters'

DIM_NAMES = ('z', 'time', 'y', 'x', 'ix', 'iy')
DIM_NAMES_TIMEAVERAGED = ('z', 'y', 'x', 'ix', 'iy')
DEFAULT_DATASET_LONG_NAMES = {'x': 'x-coordinate',
                              'y': 'y-coordinate',
                              'z': 'z-coordinate',
                              'ix': 'x-pixel-coordinate',
                              'iy': 'y-pixel-coordinate',
                              'time': 'time'}
IGNORE_ATTRS = ('mean_dx', 'mean_dy', 'mean_dz',
                'rms_dx', 'rms_dy', 'rms_dz',
                'coord_min', 'coord_max', 'coord_units', 'time_step', 'time_step_idx',
                'CLASS', 'NAME', 'DIMENSION_LIST', 'REFERENCE_LIST', 'COORDINATES')

MULTIPLANE_TITLE = 'PIV multi-plane file generated from PIVview netCDF4 files.'
PIVPLANE_TITLE = 'PIV plane file generated from PIVview netCDF4 files.'
PIVSNAPSHOT_TITLE = 'PIV snapshot file generated from a single PIVview netCDF4 file.'

PIV_FILE_TYPE_NAME = {'PIVSnapshot': 'snapshot',
                      'PIVPlane': 'single_plane',
                      'PIVMultiPlane': 'multi_plane'}


class InvalidZSourceError(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MultipleParFilesError(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def copy_attributes(attribute_dict, target_h5_object):
    for ak, av in attribute_dict.items():
        if ak not in IGNORE_ATTRS:
            target_h5_object.attrs.modify(ak, av)


def scan_for_nc_files(folder_path: Path):
    """scans for nc files (extension '.nc') in folder"""
    return sorted(folder_path.glob('*.nc'))


def scan_for_timeseries_nc_files(folder_path: Path) -> List[Path]:
    """
    Scans for nc files (extension '.nc') in folder. Omits all files that do not end with numeric character [0-9]
    or end with [0-9] and a single character.
    """
    list_of_files = sorted(folder_path.glob('*[0-9]?.nc'))
    if len(list_of_files) > 0:
        return list_of_files
    else:
        return sorted(folder_path.glob('*[0-9].nc'))


class PIVConversionInputError(Exception):

    def __init__(self, name, piv_converter_class):
        self.name = name
        self.piv_converter_class = piv_converter_class
        if os.path.isfile(self.name):
            ftype = 'file'
        else:
            ftype = 'directory'
        self.message = f'Read-in error while processing {ftype} "{name}" using ' \
                       f'converter class "{piv_converter_class.__class__.__name__}"'
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message} -> Make sure data input is matching class requirements!'


class PIV_Z_Source:
    """helper class to assure that user z source input option is correct"""
    allowed_strings: tuple = ('coord_min', 'coord_max', 'origin_offset', 'file')
    is_valid: bool = False
    value: any = 'coord_min'

    def __init__(self, value):
        self.value = value
        if isinstance(value, str):
            if value in self.allowed_strings:
                self.is_valid = True
        elif isinstance(self, float):
            self.is_valid = True
        if not self.is_valid:
            raise InvalidZSourceError(f'Invalid z-source: {value}')


def folder_has_nc_files(folder_path: Path):
    """checks if folder has nc files"""
    if not folder_path.is_dir():
        return False
    nc_files = list(folder_path.glob('*.nc'))
    return len(nc_files) > 0


def piv_conversion(conversion_method):
    """decorator method for code to be run after main conversion method"""

    def piv_conversion_wrapper(*args, **kwargs):
        conversion_starting_time = time.time()
        now = datetime.now()

        hdf_filename = conversion_method(*args, **kwargs)

        if args[0].hdf_filename is not None:
            # dd/mm/YY H:M:S
            dt_string = now.strftime(args[0].configuration['datetime_str'])
            with h5py.File(args[0].hdf_filename, 'r+') as h5:
                h5.attrs['creation_time'] = dt_string
                h5.attrs[DataSourceType.get_attr_name()] = DataSourceType.experimental.name
                h5.attrs[DataSource.get_attr_name()] = DataSource.particle_image_velocimetry.name
                h5.attrs['piv_data_type'] = PIV_FILE_TYPE_NAME[args[0].__class__.__name__]
                h5.attrs['piv_dimension'] = '2D2C' if args[0].is_2d2c else '2D3C'
                _configuration = None
                for k, v in args[0].configuration.items():
                    if isinstance(v, conventions.StandardizedNameTable):
                        _configuration = args[0].configuration.copy()
                        _configuration[k] = str(v)
                if _configuration is None:
                    h5.attrs['configuration'] = json.dumps(args[0].configuration)
                else:
                    h5.attrs['configuration'] = json.dumps(_configuration)
                h5.attrs['__h5rdmtoolbox_version__'] = __version__
                class_name = args[0].__class__.__name__
                if class_name == 'PIVSnapshot':
                    h5.attrs['title'] = PIVSNAPSHOT_TITLE
                elif class_name == 'PIVPlane':
                    h5.attrs['title'] = PIVPLANE_TITLE
                elif class_name == 'PIVMultiPlane':
                    h5.attrs['title'] = MULTIPLANE_TITLE

                if class_name == 'PIVMultiPlane':
                    # attach scale for non-time-averaged dataset:
                    for k in h5.keys():
                        if not isinstance(h5[k], h5py.Group):
                            if args[0].one_freq_for_all_planes:
                                if k not in DIM_NAMES:
                                    for ic, c in enumerate(('z', 'time', 'y', 'x')):
                                        h5[k].dims[ic].attach_scale(h5[c])
                            else:
                                if k not in DIM_NAMES:
                                    for ic, c in enumerate(('z', 'y', 'x')):
                                        h5[k].dims[ic].attach_scale(h5[c])

                # assign standard_names if available
                for name, ds in h5.items():
                    if isinstance(ds, h5py.Dataset):
                        if 'standard_name' not in ds.attrs:
                            if name in pivview_to_standardnames_dict:
                                ds.attrs['standard_name'] = pivview_to_standardnames_dict[name]
        args[0].conversion_time = time.time() - conversion_starting_time
        return hdf_filename

    return piv_conversion_wrapper


class PIVConverter:
    conversion_time: float = -1
    name: Path  # path to file or folder
    hdf_filename: Path = None  # target hdf filename
    vtk_file_name: Path = None  # filename in case class was exported to vtk

    # array shape info:
    nz: int = 0  # number of data points in z-direction
    nt: int = 0  # number of data points in time
    ny: int = 0  # number of data points in y-direction
    nx: int = 0  # number of data points in x-direction

    # conversion settings to be used by a convert()-method:
    configuration: dict

    @property
    def shape(self):
        return tuple([n for n in (self.nz, self.nt, self.ny, self.nx) if n > 0])

    def __init__(self, name):
        self.name = Path(name)

    def convert(self, target_hdf_filename: Path = None, configuration: Union[Dict, Path, None] = None):
        """kind-of abstract class processing some things before actual conversion process that is individual
        for any subclass"""
        if configuration is None:
            self.configuration = config  # set current config
        elif isinstance(configuration, dict):
            # update (!) the default yaml configuration
            _config = config
            _config.update(configuration)
            if check_yaml_file(_config):
                self.configuration = _config
        elif isinstance(configuration, Path):
            _configuration = read_yaml_file(configuration)
            if check_yaml_file(_configuration):
                self.configuration = _configuration
        else:
            raise TypeError(f'Unexpected type for configuration: {type(configuration)}')


class PIVNCConverter(PIVConverter):
    nz: int = 0  # number of data points in z-direction
    nt: int = 0  # number of data points in time
    ny: int = 0  # number of data points in y-direction
    nx: int = 0  # number of data points in x-direction

    def __init__(self, name):
        super().__init__(name)

    def is_snapshot(self):
        if self.name and self.name.suffix == '.nc':
            return True
        return False

    def is_plane(self):
        return folder_has_nc_files(self.name)

    def to_vtk(self, vtk_filename_wo_suffix: Path = None):
        """converts the hdf file into vtk file. only considers time averages!

        Parameters
        ----------
        vtk_filename_wo_suffix : pathlib.Path
            File name without suffix to write vtk data to.

        Returns
        -------
        None
        """
        if vtk_filename_wo_suffix is None:
            self.vtk_file_name = Path.joinpath(self.hdf_filename.parent, self.hdf_filename.stem)
        else:
            vtk_filename_wo_suffix = Path(vtk_filename_wo_suffix)
            # remove suffix if user has not followed the docstring:
            if vtk_filename_wo_suffix.suffix != '':
                self.vtk_file_name = Path.joinpath(vtk_filename_wo_suffix.parent, vtk_filename_wo_suffix.stem)
            else:
                self.vtk_file_name = vtk_filename_wo_suffix


def result_3D_to_vtk(data3, target='', save_to_file=False):
    """
    Saves 3D interpolated data in VTK regular grid format. Preconditioning to
    fortran style is handled in core function. Either to file or back to mayavi.

    Parameters
    ----------
    data3 : dict
        Input full 3D data as specified from above.
    target : Path, optional=''
        If to file, this is the target location.
    save_to_file : bool, optional=False
        Create File?

    Returns
    -------
    vtkRectilinearGrid
        The vtk gridded data for use in mayavi.

    Notes
    -----
    Credits to M. Elfner (ITS, Karlsruhe Institute of Technology)

    """
    try:
        from pyevtk.hl import gridToVTK
    except ImportError:
        ImportError('Package pyevtk not installed.')
    from ..vtk_utils import precondition_grid_data, numpy_data_to_rectgrid
    point_data_rg, (xr, yr, zr) = precondition_grid_data(data3)

    file = None
    if save_to_file:
        file = gridToVTK(str(target), xr, yr, zr, pointData=point_data_rg)

    vtk_data = numpy_data_to_rectgrid(xr, yr, zr, point_data_rg)

    return vtk_data, file


def get_parameter_file_from_plane(folder_directory: Path) -> Union[Path, None]:
    """return parameter/config file. If fails, None is returned"""
    parameter_files = list(folder_directory.glob('*.par'))
    config_files = list(folder_directory.glob('*.cfg'))
    if len(parameter_files) > 0 and len(config_files) > 0:
        raise FileExistsError('Parameter and config file found. Only one of it must be given!')

    files = parameter_files + config_files

    if len(files) == 1:
        filename = files[0]

    if len(files) == 0:
        print(f'No parameter (*.par) file found for plane {folder_directory}')
        return None

    if len(files) > 1:
        # Check if any of them is called *plane*.cfg
        potential_plane_cfg_files = [p for p in list(files) if 'plane' in p.stem]
        if len(potential_plane_cfg_files) == 1:
            logging.info(f'More than one parameter file found in plane {folder_directory}. The following will be used: '
                         f'{potential_plane_cfg_files[0]}')
            filename = files[0]

        elif len(potential_plane_cfg_files) == 0:
            raise MultipleParFilesError(f'More than one parameter file found in plane {folder_directory} and none of '
                                        f'them is the *plane*.cfg file. Make sure that there is only one, or at least '
                                        f'one only that contains *plane* keyword!')
        elif len(potential_plane_cfg_files) >= 1:
            raise MultipleParFilesError(f'More than one parameter file containing *plane* keyword was found in plane '
                                        f'{folder_directory}. Make sure that there is only one!')

    return filename


def compute_running_std(h5group, configuration, ddof):
    attrs_unit_name = configuration['attrs_unit_name']
    if configuration['post']['grpname'] not in h5group:
        gpost = h5group.create_group(configuration['post']['grpname'])
        gpost.attrs['long_name'] = configuration['post']['grpdesc']
    else:
        gpost = h5group[configuration['post']['grpname']]
    if configuration['post']['running_std']['grpname'] not in gpost:
        grstd = gpost.create_group(configuration['post']['running_std']['grpname'])
        grstd.attrs['long_name'] = configuration['post']['running_std']['grpdesc']
    else:
        grstd = h5group[configuration['post']['running_std']['grpname']]

    for ds_name in configuration['post']['running_std']['dataset_names']:
        if not ds_name in h5group:
            logger.error(f'The dataset "{ds_name}" is not part of the HDF5 file. A running '
                         f'std cannot be computed for it.')
        else:
            rstd = running_std(h5group[ds_name][:], axis=1, ddof=ddof)
            ds = grstd.create_dataset(ds_name, data=rstd)
            ds.attrs[attrs_unit_name] = h5group[ds_name].attrs[attrs_unit_name]
            ds.attrs['long_name'] = f'Running standard deviation of the {ds_name}'
            if h5group['dx'].ndim == 4:
                for ic, c in enumerate(('z', 'time', 'y', 'x')):
                    ds.dims[ic].attach_scale(h5group[c])
            else:
                for ic, c in enumerate(('time', 'y', 'x')):
                    ds.dims[ic].attach_scale(h5group[c])


def compute_running_mean(h5group, configuration):
    attrs_unit_name = configuration['attrs_unit_name']
    if configuration['post']['grpname'] not in h5group:
        gpost = h5group.create_group(configuration['post']['grpname'])
        gpost.attrs['long_name'] = configuration['post']['grpdesc']
    else:
        gpost = h5group[configuration['post']['grpname']]
    if configuration['post']['running_mean']['grpname'] not in gpost:
        grmean = gpost.create_group(configuration['post']['running_mean']['grpname'])
        grmean.attrs['long_name'] = configuration['post']['running_mean']['grpdesc']
    else:
        grmean = h5group[configuration['post']['running_mean']['grpname']]

    for ds_name in configuration['post']['running_mean']['dataset_names']:
        if not ds_name in h5group:
            logger.error(f'The dataset "{ds_name}" is not part of the HDF5 file. A running '
                         f'mean cannot be computed for it.')
        else:
            rmean = running_mean(h5group[ds_name][:], axis=1)
            ds = grmean.create_dataset(ds_name, data=rmean)
            ds.attrs[attrs_unit_name] = h5group[ds_name].attrs[attrs_unit_name]
            ds.attrs['long_name'] = f'Running mean of the {ds_name}'
            if h5group['dx'].ndim == 4:
                for ic, c in enumerate(('z', 'time', 'y', 'x')):
                    ds.dims[ic].attach_scale(h5group[c])
            else:
                for ic, c in enumerate(('time', 'y', 'x')):
                    ds.dims[ic].attach_scale(h5group[c])
