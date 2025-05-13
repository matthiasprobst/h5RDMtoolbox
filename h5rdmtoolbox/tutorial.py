"""
Tutorial module providing easy access to particular data.
"""
import os
import pathlib
from typing import List

import numpy as np
import xarray as xr
from rdflib import FOAF

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.utils import generate_temporary_directory
from h5rdmtoolbox.wrapper.core import File

__this_dir__ = pathlib.Path(__file__).parent
testdir = __this_dir__ / '../tests/data'

TutorialConventionZenodoRecordID = 15389242
TutorialSNTZenodoRecordID = 10428795


def get_standard_name_table_yaml_file() -> pathlib.Path:
    """Return the path to the standard name table yaml file"""
    return __this_dir__ / 'data/tutorial_standard_name_table.yaml'


def get_convention_yaml_filename() -> pathlib.Path:
    """Return the path to the convention yaml file"""
    return __this_dir__ / 'data/tutorial_convention.yaml'


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
        contact_persons = ('Mike', 'Ellen', 'John', 'Susi')
        db_file_type = ('fan_case', 'piv_case')

        file_ids = range(n_files)
        vfrs = np.random.uniform(0, 0.1, n_files)
        for fid, vfr in zip(file_ids, vfrs):

            # select a random directory:
            ifolder = np.random.randint(0, len(_folders))
            # create folder if not exist:
            os.makedirs(folders[ifolder], exist_ok=True)

            filename = pathlib.Path(folders[ifolder]) / f'repofile_{fid:05d}.hdf'
            with File(filename, 'w') as h5:
                h5.attrs['contact_person'] = contact_persons[np.random.randint(4)]
                h5.rdf['contact_person'].name = 'http://www.w3.org/ns/prov#Person'

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
                    g = h5.create_group('timeAverages',
                                        attrs=dict(long_name='time averaged data'))
                    g.create_dataset('u', attrs={'units': 'm/s', 'long_name': 'mean u-component'},
                                     shape=(zplanes, 64, 86, 2))
                    g.create_dataset('v', attrs={'units': 'm/s', 'long_name': 'mean v-component'},
                                     shape=(zplanes, 64, 86, 2))
                    g.rdf['units'].name = 'http://qudt.org/schema/qudt/Unit'

    @staticmethod
    def generate_test_files(n_files: int = 5) -> List[pathlib.Path]:
        """Generate a nested filestructure of hdf files and return list of the filenames"""
        tocdir = generate_temporary_directory('test_repo')
        Database.build_test_repo(tocdir, n_files=n_files)
        return sorted(tocdir.rglob('*.hdf'))


np.random.seed(100)


class FlowDataset(File):
    """FlowDataset tutorial data interface class"""

    def __init__(self, x=11, y=11, z=None, u=None, v=None, w=None):
        """Create an HDF5 file containing velocity data."""
        super().__init__()
        if isinstance(x, int):
            xmin = np.random.randint(-100, 100 + 1)
            xmax = np.random.randint(-100, 100 + 1)
            x = np.linspace(xmin, xmax, x)
        elif isinstance(x, (list, tuple)):
            a, b, n = x
            x = np.sort((b - a) * np.random.random_sample(n) + a)
        self.create_dataset('x', x,
                            attrs=dict(units='m', standard_name='x_coordinate'),
                            make_scale=True)
        if isinstance(y, int):
            ymin = np.random.randint(-100, 100 + 1)
            ymax = np.random.randint(-100, 100 + 1)
            y = np.linspace(ymin, ymax, y)
        elif isinstance(y, (list, tuple)):
            a, b, n = y
            y = np.sort((b - a) * np.random.random_sample(n) + a)
        self.create_dataset('y', y,
                            attrs=dict(units='m', standard_name='y_coordinate'),
                            make_scale=True)
        if z is not None:
            if isinstance(z, int):
                zmin = np.random.randint(-100, 100 + 1)
                zmax = np.random.randint(-100, 100 + 1)
                z = np.linspace(zmin, zmax, z)
            elif isinstance(z, (list, tuple)):
                a, b, n = z
                z = np.sort((b - a) * np.random.random_sample(n) + a)
            self.create_dataset('z', z,
                                attrs=dict(units='m', standard_name='z_coordinate'),
                                make_scale=True)

        if z is None:
            ny, nx = self.y.size, self.x.size
            shape = (ny, nx)
            scales = ('y', 'x')
        else:
            nz, ny, nx = self.z.size, self.y.size, self.x.size
            shape = (nz, ny, nx)
            scales = ('z', 'y', 'x')

        if u is None:
            u = np.random.rand(*shape)
        if v is None:
            v = np.random.rand(*shape)
        if z is not None and w is None:
            w = np.random.rand(*shape)
        self.create_dataset('u', data=u,
                            attrs=dict(units='m/s', standard_name='x_velocity'),
                            attach_scales=scales)
        self.create_dataset('v', data=v,
                            attrs=dict(units='m/s', standard_name='y_velocity'),
                            attach_scales=scales)
        if z is not None:
            self.create_dataset('w', data=w,
                                attrs=dict(units='m/s', standard_name='z_velocity'),
                                attach_scales=scales)


def generate_sample_file() -> pathlib.Path:
    """Generate a sample hdf file with a velocity and pressure dataset"""
    with h5tbx.File() as h5:
        h5.attrs.write_iso_timestamp(name='timestamp',
                                     dt=None)  # writes the current date time in iso format to the attribute
        h5.attrs['project'] = 'tutorial'
        contact_grp = h5.create_group('contact')
        contact_grp.attrs['name', FOAF.firstName] = 'John'
        contact_grp.attrs['surname', FOAF.lastName] = 'Doe'

        h5.attrs['check_value'] = 0
        h5.create_dataset('pressure1', data=np.random.random(size=10) * 800,
                          attrs=dict(units='Pa', standard_name='pressure',
                                     check_value=-140.3))
        h5.create_dataset('velocity', data=[1, 2, -1],
                          attrs=dict(units='m/s', standard_name='velocity',
                                     check_value=14.2))
        g = h5.create_group('group1', attrs={'check_value': 0})
        g.create_dataset('velocity', data=[4, 0, -3, 12, 3], attrs=dict(units='m/s', standard_name='velocity'))
        g = h5.create_group('group2')
        g.attrs['check_value'] = 0
        g.create_dataset('velocity', data=[12, 11.3, 4.6, 7.3, 8.1],
                         attrs=dict(units='m/s', standard_name='velocity',
                                    check_value=30.2))
        g.create_dataset('z', data=5.4, attrs=dict(units='m', standard_name='z_coordinate'))
        g.create_dataset('pressure2', data=np.random.random(size=10),
                         attrs=dict(units='kPa', standard_name='pressure',
                                    check_value=-10.3))
    return h5.hdf_filename


def _upload_tutorial_data_to_zenodo():
    """Upload the convention yaml file to Zenodo. Should only be called by the developer.
    A valid Zenodo (not sandbox!) token with write permission is needed!"""
    from h5rdmtoolbox.repository import zenodo

    repo = zenodo.ZenodoRecord(TutorialConventionZenodoRecordID)

    description = """<p>A YAML file containing definitions of standard attributes used as part of the documentation of the <a href="http://h5rdmtoolbox.readthedocs.io/">h5RDMtoolbox</a>. It serves as a <a href="https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/convention/index.html">convention</a> on how attributes are used in HDF5 files.</p>
    <p>Works with h5RDMtoolbox&gt;v1.0.0.</p>
    <p>`</p>"""

    current_metadata = repo.get_metadata()
    print(current_metadata)
    current_metadata['description'] = description
    current_metadata['title'] = 'H5TBX Tutorial Convention'
    from h5rdmtoolbox import __author_orcid__
    current_metadata['creators'] = [{'name': 'Probst, Matthias', 'orcid': __author_orcid__}, ]
    current_metadata['version'] = '1.0.0'
    current_metadata['upload_type'] = 'other'
    current_metadata['prereserve_doi'] = None

    repo.set_metadata(metadata=current_metadata)

    # upload the convention yaml file
    from h5rdmtoolbox.convention import yaml2jsonld
    convention_filename = get_convention_yaml_filename()
    # repo.upload_file(convention_filename, metamapper=None)
    jsonld_filename = yaml2jsonld(get_convention_yaml_filename(),
                                  file_url=f"{repo.base_url}/record/{repo.rec_id}/files/{convention_filename.name}")
    repo.upload_file(jsonld_filename, metamapper=None, overwrite=True)
    repo.publish()


if __name__ == '__main__':
    _upload_tutorial_data_to_zenodo()
