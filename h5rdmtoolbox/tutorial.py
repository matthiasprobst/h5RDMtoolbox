import os
import pathlib
import shutil
from typing import Tuple, List

import numpy as np
import xarray as xr

from h5rdmtoolbox import H5File
from ._user import testdir
from .utils import generate_temporary_directory, generate_temporary_filename


class PIVview:
    """PIVview tutorial class"""

    @staticmethod
    def get_parameter_file() -> pathlib.Path:
        """Return pivview parameter file"""
        return testdir / 'PIV/piv_challenge1_E/piv_parameters.par'

    @staticmethod
    def get_plane_directory() -> pathlib.Path:
        """Return the path to the respective example PIV plane"""
        return testdir / 'PIV/piv_challenge1_E/'

    @staticmethod
    def get_multiplane_directories() -> Tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
        """Copies the piv_challenge1_E data to three directories in the tmp directory
        Two planes have three nc files, one plane has 2 nc files only"""
        try:
            from netCDF4 import Dataset as ncDataset
        except ImportError:
            raise ImportError('Package netCDF4 is not installed. Either install it '
                              'separately or install the repository with pip install h5RDMtolbox [piv]')

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
        """Return a list of sorted nc files"""
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


class OpenPIV:
    """OpenPIV tutorial class"""

    @staticmethod
    def get_snapshot_txt_file():
        """Return snapshot piv result from ILA vortex"""
        return testdir / f'PIV/openpiv/vortex.txt'

    @staticmethod
    def get_parameter_file():
        """Return openpiv parameters as file"""
        return testdir / f'PIV/openpiv/openpiv.par'


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


def get_H5PIV(name: str, mode: str = 'r') -> pathlib.Path:
    """Return the HDF filename of a tutoral case."""
    from .h5wrapper import H5PIV
    if name == 'minimal_flow':
        fname = testdir / 'minimal_flow.hdf'
        tmp_filename = shutil.copy2(fname, generate_temporary_filename(suffix='.hdf'))
        if tmp_filename.exists():
            return H5PIV(tmp_filename, mode=mode)
        else:
            raise FileNotFoundError(tmp_filename)
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
        tmp_fname = shutil.copy2(vortex1_hdf_fname, generate_temporary_filename(suffix='.hdf'))

        # add the images to the hdf file:
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


class Conventions:
    """Tutorial methods for package conventions"""

    @staticmethod
    def fetch_cf_standard_name_table():
        """download cf-standard-name-table"""
        from h5rdmtoolbox.conventions.identifier import CFStandardNameTable
        try:
            import pooch
        except ImportError:
            raise ImportError(f'Package "pooch" is needed to download the file cf-standard-name-table.xml')
        file_path = pooch.retrieve(
            url="https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml",
            known_hash='4c29b5ad70f6416ad2c35981ca0f9cdebf8aab901de5b7e826a940cf06f9bae4',
        )
        return CFStandardNameTable.from_xml(file_path)


class CFX:
    @staticmethod
    def get_cfx_filename():
        return testdir / f'CFD/AnsysCFX/channel_plus_cyl.cfx'


class Database:
    """Database tutorial data interface class"""

    @staticmethod
    def build_test_repo(repo_dir, n_files: int = 100):
        """
        sample file with some groups, datasets and attributes
        Data is stored with actual names at correct hdf-path location,
        but the file is just not complete and data is randomly created
        and has no physical meaning.
        """

        def _get_pressure(v):
            """a random pressure curve. input volume rate [0, 0.1] and
            get a artificial pressure in return"""
            x = np.linspace(0, 0.1, 101)
            p = -60 / np.max(x) ** 2 * v ** 2 + 60
            return p

        _folders = ('d1', 'd2', 'd3', 'd1/d11', 'd1/d11/d111', 'd2/d21')
        folders = [os.path.join(repo_dir, _f) for _f in _folders]
        operators = ('Mike', 'Ellen', 'John', 'Susi')
        db_file_type = ('fan_case', 'piv_case')

        file_ids = range(n_files)
        vfrs = np.random.uniform(0, 0.1, n_files)
        for fid, vfr in zip(file_ids, vfrs):

            # select a random directory:
            ifolder = np.random.randint(0, len(_folders))
            # create folder if not exist:
            os.makedirs(folders[ifolder], exist_ok=True)

            filename = os.path.join(folders[ifolder], f'repofile_{fid:05d}.hdf')
            with H5File(filename, 'w') as h5:
                h5.attrs['operator'] = operators[np.random.randint(4)]
                __ftype__ = db_file_type[np.random.randint(2)]
                h5.attrs['__db_file_type__'] = __ftype__

                if __ftype__ == 'fan_case':
                    op = h5.create_group('operation_point', attrs={'long_name': 'Operation point data group'})

                    _ptot = _get_pressure(vfr)
                    _ptot_vec = np.random.rand(100) - 0.5 + _ptot
                    ds = op.create_dataset('ptot',
                                           data=_ptot_vec, attrs={'units': 'Pa', 'long_name': 'Pressure increase'})
                    ds.attrs['mean'] = np.mean(_ptot_vec)
                    ds.attrs['std'] = np.std(_ptot_vec)

                    _vfr_vec = np.random.rand(100) - 0.5 + vfr
                    ds = op.create_dataset('vfr',
                                           attrs={'units': 'm^3/s', 'long_name': 'volume flow_utils rate'},
                                           data=_vfr_vec)
                    ds.attrs['mean'] = np.mean(_vfr_vec)
                    ds.attrs['std'] = np.std(_vfr_vec)
                else:
                    zplanes, timesteps = 2, 5
                    h5.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'u-component'},
                                      shape=(zplanes, timesteps, 64, 86, 2))
                    h5.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'v-component'},
                                      shape=(zplanes, timesteps, 64, 86, 2))
                    g = h5.create_group('timeAverages', long_name='time averaged data')
                    g.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'mean u-component'},
                                     shape=(zplanes, 64, 86, 2))
                    g.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'mean v-component'},
                                     shape=(zplanes, 64, 86, 2))

    @staticmethod
    def generate_test_files() -> List[pathlib.Path]:
        """Generate many files in a nested folders"""
        tocdir = generate_temporary_directory('test_repo')
        Database.build_test_repo(tocdir)
        return list(tocdir.rglob('*.hdf'))
