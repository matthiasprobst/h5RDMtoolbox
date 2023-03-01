"""
Tutorial module providing easy access to particular data.
"""
import numpy as np
import os
import pathlib
import xarray as xr
from typing import List

from .utils import generate_temporary_directory
from .wrapper.cflike import H5File as CFH5File


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


class Conventions:
    """Tutorial methods for package conventions"""

    @staticmethod
    def fetch_cf_standard_name_table():
        """download cf-standard-name-table"""
        from h5rdmtoolbox.conventions.cflike.standard_name import StandardNameTable
        url = "https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml"
        return StandardNameTable.from_web(url)


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

            filename = pathlib.Path(folders[ifolder]) / f'repofile_{fid:05d}.hdf'
            with CFH5File(filename, 'w') as h5:
                h5.attrs['operator'] = operators[np.random.randint(4)]
                if fid % 2:
                    __ftype__ = db_file_type[0]
                else:
                    __ftype__ = db_file_type[1]
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
                    h5.create_dataset('x', data=range(86), attrs={'units': 'm', 'long_name': 'x-coordinate'},
                                      make_scale=True)
                    h5.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'u-component'},
                                      shape=(zplanes, timesteps, 64, 86, 2),
                                      attach_scales=(None, None, None, 'x', None))
                    h5.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'v-component'},
                                      shape=(zplanes, timesteps, 64, 86, 2),
                                      attach_scales=(None, None, None, 'x', None))
                    g = h5.create_group('timeAverages', long_name='time averaged data')
                    g.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'mean u-component'},
                                     shape=(zplanes, 64, 86, 2))
                    g.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'mean v-component'},
                                     shape=(zplanes, 64, 86, 2))

    @staticmethod
    def generate_test_files(n_files: int = 5) -> List[pathlib.Path]:
        """Generate a nested filestructure of hdf files and return list of the filenames"""
        tocdir = generate_temporary_directory('test_repo')
        Database.build_test_repo(tocdir, n_files=n_files)
        return sorted(tocdir.rglob('*.hdf'))
