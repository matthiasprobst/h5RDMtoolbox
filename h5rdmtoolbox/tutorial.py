# import pooch

#
# file_path = pooch.retrieve(
#     # URL to one of Pooch's test files
#     url="https://www.pivtec.com/download/samples/pivimg1.zip",
#     known_hash="ef53ce7e2cbcfdac75cf218b4164754a7c41cb1341e1d2311cc2f32643cc9693",
#     processor=pooch.Unzip(extract_dir=user_data_dir / 'tutorial/PIV/'),
# )
import pathlib
import shutil
from typing import Tuple

import numpy as np
import xarray as xr
from . import utils

try:
    from netCDF4 import Dataset as ncDataset
except ImportError:
    raise ImportError('Package netCDF4 is not installed.')

from .utils import generate_temporary_directory
from . import testdir


class PIVview:

    @staticmethod
    def get_plane_directory() -> pathlib.Path:
        """Returns the path to the respective example PIV plane"""
        return testdir / 'PIV/piv_challenge1_E/'

    @staticmethod
    def get_multiplane_directories() -> Tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
        """Copies the piv_challenge1_E data to three directories in the tmp directory
        Two planes have three nc files, one plane has 2 nc files only"""

        def _set_z_in_nc(nc_filename, z_val):
            with ncDataset(nc_filename, 'r+') as nc:
                nc.setncattr('origin_offset_z', z_val)
                for k, v in nc.variables.items():
                    if 'coord_min' in nc[k].ncattrs():
                        coord_min = nc[k].getncattr('coord_min')
                        coord_min[-1] = z_val
                        nc[k].setncattr('coord_min', coord_min)
                        coord_max = nc[k].getncattr('coord_max')
                        coord_max[-1] = z_val
                        nc[k].setncattr('coord_max', coord_max)

        src_dir = testdir / 'PIV/piv_challenge1_E/'
        nc_files = sorted(src_dir.glob('*[0-9].nc'))

        plane0 = generate_temporary_directory(prefix='mplane/')
        _ = shutil.copy2(src_dir / 'piv_parameters.par', plane0.joinpath('piv_parameter.par'))
        dst = shutil.copy2(nc_files[0], plane0.joinpath('f0.nc'))
        _set_z_in_nc(dst, -5.)
        dst = shutil.copy2(nc_files[1], plane0.joinpath('f1.nc'))
        _set_z_in_nc(dst, -5.)
        dst = shutil.copy2(nc_files[2], plane0.joinpath('f2.nc'))
        _set_z_in_nc(dst, -5.)

        plane1 = generate_temporary_directory(prefix='mplane/')
        _ = shutil.copy2(src_dir / 'piv_parameters.par', plane1.joinpath('piv_parameter.par'))
        dst = shutil.copy2(nc_files[3], plane1.joinpath('f0.nc'))
        _set_z_in_nc(dst, 0.)
        dst = shutil.copy2(nc_files[4], plane1.joinpath('f1.nc'))
        _set_z_in_nc(dst, 0.)
        dst = shutil.copy2(nc_files[5], plane1.joinpath('f2.nc'))
        _set_z_in_nc(dst, 0.)

        plane2 = generate_temporary_directory(prefix='mplane/')
        _ = shutil.copy2(src_dir / 'piv_parameters.par', plane2.joinpath('piv_parameter.par'))
        dst = shutil.copy2(nc_files[6], plane2.joinpath('f0.nc'))
        _set_z_in_nc(dst, 10.)
        dst = shutil.copy2(nc_files[7], plane2.joinpath('f1.nc'))
        _set_z_in_nc(dst, 10.)

        return plane0, plane1, plane2

    @staticmethod
    def get_snapshot_nc_files():
        """returns a list of sorted nc files"""
        return sorted((testdir / f'PIV/piv_challenge1_E/').glob('E00A*.nc'))

    @staticmethod
    def get_avg_file():
        return testdir.joinpath('PIV/piv_challenge1_E/avg.dat')

    @staticmethod
    def get_rms_file():
        return testdir.joinpath('PIV/piv_challenge1_E/rms.dat')

    @staticmethod
    def get_reyn_file():
        return testdir.joinpath('PIV/piv_challenge1_E/reyn.dat')


def get_xr_dataset(name):
    """Loads a xr.Dataset"""

    def _init_2d_flow_xarray_dataset(x, y, coord_units='m', velocity_units='m/s'):
        if not x.ndim == 1:
            raise ValueError(f'x-coord must be 1D but is {x.ndim}D')
        if not y.ndim == 1:
            raise ValueError(f'y-coord must be 1D but is {x.ndim}D')

        x = xr.DataArray(dims='x', data=x, attrs={'units': coord_units, 'standard_name': 'x_coordinate'})
        y = xr.DataArray(dims='y', data=y, attrs={'units': coord_units, 'standard_name': 'x_coordinate'})

        u_ds = xr.DataArray(dims=('y', 'x'), data=np.zeros((y.size, x.size)),
                            attrs={'units': velocity_units, 'standard_name': 'x_velocity'})
        v_ds = xr.DataArray(dims=('y', 'x'), data=np.zeros((y.size, x.size)),
                            attrs={'units': velocity_units, 'standard_name': 'y_velocity'})
        w_ds = xr.DataArray(dims=('y', 'x'), data=np.zeros((y.size, x.size)),
                            attrs={'units': velocity_units, 'standard_name': 'z_velocity'})
        mag_ds = xr.DataArray(dims=('y', 'x'), data=np.zeros((y.size, x.size)),
                              attrs={'units': velocity_units, 'standard_name': 'magnitude_of_velocity'})

        return xr.Dataset(data_vars={'u': u_ds,
                                     'v': v_ds,
                                     'w': w_ds,
                                     'mag': mag_ds},
                          coords={'x': x, 'y': y},
                          attrs={'long_name': 'velocity data'}
                          )

    def couette2d(x, y, max_velocity: float, flow_direction: str = 'x',
                  coord_units='m', velocity_units='m/s', y0='min'):
        """
        Parameters
        ----------
        x, y: np.ndarray (1d)
            x- and y-coordinates
        max_velocity: float
            Max velocity
        flow_direction: str, optional='x
            'x' or 'y'
        coord_units: str, optional='m'
            Coordinate units
        velocity_units: str, optional='m/s'
            Velocity units
        y0: str, optional='min'
            specifies the y position of the standing wall. Options are
            'min' or 'max'
        """
        velocity = _init_2d_flow_xarray_dataset(x, y, coord_units, velocity_units)

        if flow_direction[:] == 'x':
            if y0 == 'min':
                u = velocity.u.y / velocity.u.y.max() * max_velocity
            elif y0 == 'max':
                u = (1 - velocity.u.y / velocity.u.y.max()) * max_velocity
            else:
                raise ValueError(f'Parameter y0 must be "min" or "max" and not "{y0}"')
            for ix in range(velocity.u.shape[1]):
                velocity.u[:, ix] = u
            velocity['v'][:] = 0
        elif flow_direction[:] == 'y':
            v = velocity.v.x / velocity.v.x.max() * max_velocity
            for ix in range(velocity.v.shape[1]):
                velocity.v[:, ix] = v
            velocity['u'][:] = 0
        velocity['w'][:] = 0
        velocity['mag'][:] = np.sqrt(velocity.u ** 2 + velocity.v ** 2)
        return velocity

    def poiseuille2D(x, y, max_velocity: float, flow_direction: str = 'x',
                     coord_units='m', velocity_units='m/s') -> xr.Dataset:
        """
        Parameters
        ----------
        x, y: np.ndarray (1d)
            x- and y-coordinates
        max_velocity: float
            Max velocity
        flow_direction: str, optional='x
            'x' or 'y'
        coord_units: str, optional='m'
            Coordinate units
        velocity_units: str, optional='m/s'
            Velocity units
        """
        velocity = _init_2d_flow_xarray_dataset(x, y, coord_units, velocity_units)

        if flow_direction == 'x':
            R = (velocity.y.max() - np.min(velocity.y)) / 2
            r = velocity.y - R
        elif flow_direction == 'y':
            R = (velocity.x.max() - np.min(velocity.x)) / 2
            r = velocity.x - R
        else:
            raise ValueError(f'Parameter "R" must be "x" or "y" and not "{flow_direction}".')
        a = -max_velocity / R ** 2
        c = max_velocity
        vel = a * r ** 2 + c
        if flow_direction == 'x':
            for ix in range(velocity.u.shape[1]):
                velocity.u[:, ix] = vel
            velocity['v'][:] = 0
        if flow_direction == 'y':
            for iy in range(velocity.v.shape[0]):
                velocity.v[iy, :] = vel
            velocity['u'][:] = 0
        velocity['w'][:] = 0
        velocity['mag'][:] = np.sqrt(velocity.u ** 2 + velocity.v ** 2)

        return velocity

    av_names = ['poiseuille2D', 'couette2d']
    if name not in av_names:
        raise Exception(f'Tutorial dataset with name "{av_names} not available')

    if name.lower() == 'couette2d':
        return couette2d(np.linspace(0, 4, 2), np.linspace(0, 4, 10), 2)

    if name.lower() == 'poiseuille2d':
        return poiseuille2D(np.linspace(0, 4, 2), np.linspace(0, 4, 10), 2)


def get_H5PIV(name, mode) -> pathlib.Path:
    """Returns the HDF filename of a tutoral case."""
    from .h5wrapper import H5PIV
    if name == 'minimal_flow':
        fname = testdir / 'minimal_flow.hdf'
        if fname.exists():
            return H5PIV(fname, mode=mode)
        else:
            raise FileNotFoundError(fname)
    elif name == 'vortex_snapshot':

        def _rgb2gray(rgb):
            """turns a rgb image (3D array) into a grayscale image (2D). If input is 2D array is just returned"""
            if rgb.ndim == 2:
                # logger.info('Input image is already grayscale!')
                return rgb
            if not rgb.ndim == 3:
                raise ValueError(f'Not a RGB image. Expecting a 3D image, not {rgb.ndim}D.')
            r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
            gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
            return gray

        vortex1_hdf_fname = testdir / 'PIV/vortexpair/vortex1.hdf'
        tmp_fname = utils.generate_temporary_filename(suffix='.hdf')

        with H5PIV(vortex1_hdf_fname, 'r+') as h5:
            h5.saveas(tmp_fname, keep_old=True)

        with H5PIV(tmp_fname, 'r+') as h5:
            h5.create_dataset_from_image(testdir / 'PIV/vortexpair/vp1a.tif', 'imgA',
                                         long_name='piv_image_a',
                                         ufunc=_rgb2gray)
            h5.create_dataset_from_image(testdir / 'PIV/vortexpair/vp1b.tif', 'imgB',
                                         long_name='piv_image_b',
                                         ufunc=_rgb2gray)
        return H5PIV(tmp_fname, mode=mode)
    else:
        raise NameError(f'Invalid name')