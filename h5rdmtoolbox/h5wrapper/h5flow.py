import logging
from pathlib import Path
from typing import Tuple, List, Union

import h5py
import numpy as np
import xarray as xr
from pandas import read_csv
from pint_xarray import unit_registry as ureg

from . import config
from .accessory import SpecialDataset, register_special_dataset
from .h5file import H5File, H5Group, H5FileLayout
from .. import user_data_dir
from ..conventions.standard_names import FluidConvention

logger = logging.getLogger(__package__)
DIM_NAMES = ('z', 'time', 'y', 'x')


#
# def _find_time_scale(ds):
#     i_time = None
#     for i, d in enumerate(ds.dims):
#         for j in range(len(d)):
#             if d[j].attrs.get('standard_name') == 'time':
#                 i_time = (i, j)
#                 break
#         if i_time is not None:
#             break
#     if i_time is None:
#         raise ValueError(f'Dataset with standard name "time" not found as attached scales. '
#                          f'Cannot determine axis along which to compute reynolds stresses.')
#     return i_time


# def _get_reyn(obj):
#     return _build_xarray_dataset([obj[n] for n in ('uu', 'uv', 'uw', 'vv', 'vw', 'ww')], 'reynolds stresses')
#
# def _build_xarray_dataset(names, long_name):
#     xrds = xr.merge([n[:] for n in names])
#     xrds.attrs['long_name'] = long_name
#     return xrds


class XRVectorDataset(xr.Dataset):
    __slots__ = ()

    def get_by_sn(self, standard_name: str, on_multiple='list'):
        """Returns the dataset corresponding to the standard_name.
        If none is found None is returned.
        If 1 is found, the dataset is returned
        If multiples are found list or error is raise, depending on parameter on_multiple"""
        candidates = []
        for v in self.values():
            if 'standard_name' in v.attrs:
                if standard_name == v.attrs['standard_name']:
                    candidates.append(v)
        if len(candidates) == 0:
            return None
        if len(candidates) == 1:
            return candidates[0]
        if on_multiple == 'list':
            return candidates
        if on_multiple == 'error':
            raise ValueError(f'Multiple datasets found with standard name {standard_name}')

    @property
    def vector_vars(self):
        _vector_datasets = [(self[dv].attrs.get('vector_component'), dv) for dv in self.data_vars if
                            'vector_component' in self[dv].attrs]
        # sort and return
        _vector_datasets.sort()
        return tuple([v[1] for v in _vector_datasets])

    def compute_magnitude(self, standard_name=None):
        """Computes the magnitude of the vector."""
        mag2 = None
        for ids, comp in enumerate(self.vector_vars):
            if mag2 is None:
                if comp in self:
                    mag2 = self[comp].pint.quantify() ** 2
            else:
                if comp in self:
                    mag2 += self[comp].pint.quantify() ** 2
        mag = np.sqrt(mag2).pint.dequantify(format=ureg.default_format)
        self['magnitude'] = mag
        self['magnitude'].attrs = mag.attrs
        if standard_name is None:
            # trying to determine a new standard name
            # TODO: compute new standard_name from standard_names of components: magnitude_of_[common_standard_name]
            component_standard_names = [self[comp].attrs.get('standard_name') for comp in self.vector_vars]
            if all(['velocity' in c for c in component_standard_names]):
                self['magnitude'].attrs['standard_name'] = 'magnitude_of_velocity'


class XRVelocityDataset(XRVectorDataset):
    """subclass of xr.Dataset to enable typical computation tasks for
    velocity data such as computation of tke, reyn, vorticity, ...

    Velocity components are u, v, w (not all must exist!). Those
    names are fixed.
    """
    __slots__ = ()

    def tke(self):
        raise NotImplementedError()

    def reyn(self):
        raise NotImplementedError()

    def vorticity(self):
        raise NotImplementedError()

    def compute_rotational_speed(self, rot_speed: float, suffix='_rot',
                                 rot_axis='z', rot_center=(0, 0)) -> None:
        """Computes and adds the rotational speed based on rot_speed [1/s] and the
        coordinates of the dataset. Center of rotation per default is (0, 0, 0) and
        axis of rotation is z. Direction of rotation is controlled by the sign of
        rot_speed. Created rotational speed data arrays have units [m/s]"""
        if not rot_axis.lower() == 'z':
            # TODO implement different rotation axes
            raise NotImplementedError('Rotation axis different than z is not implemented yet.')
        if rot_center != (0, 0):
            # TODO implement different rotation center
            raise NotImplementedError('Rotation center different than (0, 0) is not implemented yet.')

        # Code for currently available axis/rotation options:
        # turning whatever unit into [m]:
        xx, yy = np.meshgrid(self.x.values, self.y.values)
        x = xr.DataArray(name='x', dims=('y', 'x'),
                         data=xx).pint.quantify(self.x.attrs['units'])
        y = xr.DataArray(name='y', dims=('y', 'x'),
                         data=yy).pint.quantify(self.y.attrs['units'])
        r = np.sqrt(x.pint.to('m') ** 2 + y.pint.to('m') ** 2)
        omega = 2 * np.pi * rot_speed / ureg.s
        alpha = np.arctan2(y, x)
        v = omega * r * np.cos(alpha)
        u = -omega * r * np.sin(alpha)
        u = u.assign_coords({'x': self.x, 'y': self.y})
        v = v.assign_coords({'x': self.x, 'y': self.y})
        self[f'magnitude{suffix}'] = np.sqrt(u ** 2 + v ** 2).pint.dequantify(format=ureg.default_format)
        self[f'u{suffix}'] = u.pint.dequantify(format=ureg.default_format)
        self[f'v{suffix}'] = v.pint.dequantify(format=ureg.default_format)


class VectorDataset:
    """Vector class returned when get_vector() is called"""

    def __init__(self, grp, datasets, attrs=None, xrcls=None):
        self.grp = grp
        self.datasets = datasets
        self.xrcls = xrcls
        if attrs is None:
            self.attrs = {}
        else:
            self.attrs = attrs

    def __call__(self, *args, standard_names=None, names=None):
        if args and standard_names is None:
            standard_names = args
        return self.grp.get_vector(standard_names=standard_names, names=names, xrcls=self.xrcls)

    def __getitem__(self, args, new_dtype=None):
        if self.datasets is None:
            raise NameError('Could not determine component datasets')
        xrds = xr.merge([ds.__getitem__(args, new_dtype=new_dtype) for ds in self.datasets],
                        combine_attrs="drop_conflicts")
        for icomp, xrarr in enumerate(xrds):
            xrds[xrarr].attrs['vector_component'] = icomp
        xrds.attrs['long_name'] = self.attrs.pop('long_name', 'vector data')
        for k, v in self.attrs:
            xrds.attrs[k] = v
        if self.xrcls is None:
            return xrds
        else:
            return self.xrcls(xrds)


class H5FlowGroup(H5Group):
    """HDF5 Group for specifically for flow data"""

    def create_coordinates(self, x, y, z=0, time=0, coords_unit='m', time_unit='s'):
        for ds_name in ('x', 'y', 'z', 'time'):
            if ds_name in self:
                raise ValueError(f'Cannot create coordinates, because {ds_name} already exists '
                                 f'in group {self}.')

        coords = {'x': np.asarray(x), 'y': np.asarray(y), 'z': np.asarray(z), 'time': np.asarray(time)}

        compression, compression_opts = config.hdf_compression, config.hdf_compression_opts

        for coord, value in coords.items():
            if value.ndim > 1:
                raise ValueError(f'Coordinate {coord} must be 0D or 1D but is {value.ndim}D!')

        datasets = []
        for k, v in coords.items():
            if k == 'time':
                datasets.append(self.create_dataset('time', long_name='time',
                                                    units=time_unit,
                                                    standard_name='time',
                                                    maxshape=None if v.ndim == 0 else v.shape,
                                                    data=v,
                                                    compression=compression, compression_opts=compression_opts,
                                                    make_scale='time'))
            else:
                datasets.append(self.create_dataset(k, long_name=k,
                                                    standard_name=f'{k}_coordinate',
                                                    units=coords_unit,
                                                    maxshape=None if v.ndim == 0 else v.shape,
                                                    data=v,
                                                    compression=compression, compression_opts=compression_opts,
                                                    make_scale=True))
        return datasets  # return order: x,y,z,time (see dict variable "coords")

    def create_velocity_datasets(self, u: np.ndarray = None, v: np.ndarray = None, w: np.ndarray = None,
                                 compute_mag: bool = False,
                                 dim_scales: Tuple[str] = ('z', 'time', 'y', 'x'),
                                 units: str = 'm/s') -> List:

        """Creates velocity datasets u,v and w of shape (nz, nt, ny, nx). To do so, coordinate datasets must already
        exist (z, time, y, x)."""

        # TODO think about h5.VelocityDataset = xr.Dataset() --> check standard_names etc

        # TODO: check if shape of u and v and w is in agreement with z, time, y, x

        # first check if dim scales exist:
        _dim_scales = list(dim_scales)
        if not all([ds in self for ds in dim_scales]):
            raise ValueError(f'Could not create velocity data because no coordinates are available. '
                             f'Please first create them using .create_coordinates().')

        _scales = tuple([self[ds] for ds in dim_scales])
        datasets = []
        for veldata, velname, standard_name in zip((u, v, w), ('u', 'v', 'w'),
                                                   ('x_velocity', 'y_velocity', 'z_velocity')):
            if veldata is not None:
                datasets.append(self.create_dataset(velname, data=veldata, units=units, long_name=None,
                                                    standard_name=standard_name, attach_scales=_scales))
        if compute_mag:
            datasets.append(self.create_dataset('velmag', data=np.linalg.norm(
                np.stack(
                    [d[:] for d in datasets], axis=-1
                ),
                axis=-1
            ),
                                                attach_scales=_scales,
                                                units=units, standard_name='magnitude_of_velocity'))
        return datasets


class H5FlowLayout(H5FileLayout):

    def write(self):
        """The layout file has the structure of a H5Flow file. This means
        it has the required attributes, datasets and groups that are required
        for a valid H5Flow file. For each application case this is of course
        different. Such a file can be created and stored in the user directory
        and will be used to check the completeness created H5Flow files

        Dataset and group structure (attributes not shown):
        /
        /x     -> dim=(0, 1), m
        /y     -> dim=(0, 1), m
        /z     -> dim=(0, 1), m
        /time  -> dim=(0, 1), s
        """
        super().write()
        with h5py.File(self.filename, mode='r+') as h5:
            ds_x = h5.create_dataset('x', shape=(1,))
            ds_y = h5.create_dataset('y', shape=(1,))
            ds_z = h5.create_dataset('z', shape=(1,))
            ds_t = h5.create_dataset('time', shape=(1,))
            for ds in (ds_x, ds_y, ds_z, ds_t):
                ds.attrs['__ndim__'] = (0, 1)
                ds.attrs['units'] = 'm'
            ds_x.attrs['standard_name'] = 'x_coordinate'
            ds_y.attrs['standard_name'] = 'y_coordinate'
            ds_z.attrs['standard_name'] = 'z_coordinate'


class H5Flow(H5File, H5FlowGroup):
    Layout: H5FlowLayout = H5FlowLayout(Path.joinpath(user_data_dir, f'layout/H5Flow.hdf'))

    def __init__(self, name: Path = None, mode='r', title=None, sn_convention=None,
                 driver=None, libver=None, userblock_size=None,
                 swmr=False, rdcc_nslots=None, rdcc_nbytes=None, rdcc_w0=None,
                 track_order=None, fs_strategy=None, fs_persist=False, fs_threshold=1,
                 **kwds):
        if sn_convention is None:
            sn_convention = FluidConvention
        super().__init__(name, mode, title, sn_convention,
                         driver, libver, userblock_size,
                         swmr, rdcc_nslots, rdcc_nbytes, rdcc_w0,
                         track_order, fs_strategy, fs_persist, fs_threshold,
                         **kwds)

    def to_tecplot(self, filename: Path, coord_names: Union[dict, None] = None) -> Path:
        """
        Exports root group to HDF5 which can be opened with tecplot. A macro is written,
        which should be executed in order to open tecplot

        Parameter
        --------
        filename: Path
            Target HDF5 filename which is read by tecplot
        coord_names: dict or None, optional=None
            If None, the coordinates are retrieved by standard_names. The coordinate
            names can also be defined using a dictionary. The keys must be x, y, z and
            optionally time

        Returns
        ------
        filename: Path
            The created filename
        """
        raise NotImplementedError()

    def read_velocity_field_from_csv(self, csv_filename, names=('x', 'y', 'u', 'v'), structured=True, header=0, sep=',',
                                     index_col=False, coord_unit='m', vel_unit='m/s', **pandas_args):
        # TODO: put this to x2hdf.csv --> csv2grp, use this
        """
        Reads velocity data from a csv file. Units are assumed to be 'm' and 'm/s'.
        File must look like this:

        x,y,z,u,v,w
        0,1,0,0.23,14.13,2.73
        ...

        header names can be different but the order and meaning must be x-coord, y-coord,
        z-coord, u-vel, v-vel, w-vel.
        Data must be structured at this stage. In future versions unstructured data can be
        read which then will be interpolated onto an existing grid. Thus, x, y, z must
        already exist.

        Parameters
        ----------
        csv_filename
        names : tuple
            header names used for csv file.
            Reasonable headers are:
            ('x', 'y', 'u', 'v')
            ('x', 'y', 'u', 'v', 'w')
            ('x', 'y', 'z', 'u', 'v', 'w')
        structured : bool
        header : int, optional=0
        sep : str, optional=','
        index_col : bool, optional=False
        coord_unit : str, optional='m'
        vel_unit : str, optional='m/s'
        pandas_args : dict, optional={}
        """

        # to avoid having parameters twice:
        _ = pandas_args.pop('header', None)
        _ = pandas_args.pop('sep', None)
        _ = pandas_args.pop('header', 0)
        _ = pandas_args.pop('index_col', False)
        if structured:
            df = read_csv(csv_filename, index_col=index_col, header=header, names=names, sep=sep, **pandas_args)

            nx = len(np.unique(df['x'].values))
            ny = len(np.unique(df['y'].values))
            if len(names) == 6:
                _z = df['z'].values
                nz = len(np.unique(df['z'].values))
                z = _z.reshape((nz, 1, ny, nx))
            else:
                nz = 1
                z = None

            x = df['x'].values.reshape((nz, 1, ny, nx))
            y = df['y'].values.reshape((nz, 1, ny, nx))
            u = df['u'].values.reshape((nz, 1, ny, nx))
            v = df['v'].values.reshape((nz, 1, ny, nx))

            if len(names) > 4:
                w = df['w'].values.reshape((nz, 1, ny, nx))
            else:
                w = None

            if w:
                velocity_field = np.stack((u, v, w), axis=-1)
            else:
                velocity_field = np.stack((u, v), axis=-1)

            ds_x = self.create_dataset('x', long_name='x-coordinate', units=coord_unit, shape=x.shape, data=x,
                                       maxshape=(None, None, x.shape[2], y.shape[3]), make_scale=True)
            ds_y = self.create_dataset('y', long_name='y-coordinate', units=coord_unit, data=y, shape=y.shape,
                                       maxshape=(None, None, x.shape[2], y.shape[3]), make_scale=True)
            if z:
                ds_z = self.create_dataset('z', long_name='z-coordinate', units=coord_unit, shape=z.shape,
                                           maxshape=(None, None, x.shape[2], y.shape[3]), data=z,
                                           make_scale=True)
                _scale = (ds_z, None, ds_y, ds_x)
            else:
                _scale = (None, None, ds_y, ds_x)
            self.create_dataset('velocity', units=vel_unit, long_name=f'Velocity data from csv file {csv_filename}',
                                data=velocity_field, attach_scale=_scale)
            self.create_dataset('velocity_abs', units=vel_unit,
                                long_name=f'Absolute velocity data from csv file {csv_filename}',
                                data=np.linalg.norm(velocity_field, axis=-1), attach_scale=_scale)
            return x, y, velocity_field
        else:
            raise ValueError(f'Can only read structured grid data')


H5FlowGroup._h5grp = H5FlowGroup


class VectorDataset(SpecialDataset):

    @property
    def vector_vars(self):
        _vector_datasets = [(self._dset[dv].attrs.get('vector_component'), dv) for dv in self._dset.data_vars if
                            'vector_component' in self._dset[dv].attrs]
        # sort and return
        _vector_datasets.sort()
        return tuple([v[1] for v in _vector_datasets])

    def compute_magnitude(self, standard_name=None):
        """Computes the magnitude of the vector."""
        mag2 = None
        for ids, comp in enumerate(self.vector_vars):
            if mag2 is None:
                if comp in self._dset:
                    mag2 = self._dset[comp].pint.quantify() ** 2
            else:
                if comp in self:
                    mag2 += self[comp].pint.quantify() ** 2
        mag = np.sqrt(mag2).pint.dequantify(format=ureg.default_format)
        self._dset['magnitude'] = mag
        self._dset['magnitude'].attrs = mag.attrs
        if standard_name is None:
            # trying to determine a new standard name
            # TODO: compute new standard_name from standard_names of components: magnitude_of_[common_standard_name]
            component_standard_names = [self._dset[comp].attrs.get('standard_name') for comp in
                                        self.vector_vars]
            if all(component_standard_names):
                if all(['velocity' in c for c in component_standard_names]):
                    self['magnitude'].attrs['standard_name'] = 'magnitude_of_velocity'
                elif all(['displacement' in c for c in component_standard_names]):
                    self['magnitude'].attrs['standard_name'] = 'magnitude_of_displacement'


@register_special_dataset("DisplacementVector", H5Group)
class DisplacementDataset(VectorDataset):
    standard_names = ('x_displacement', 'y_displacement')


@register_special_dataset("VelocityVector", H5Group)
class VelocityDataset(VectorDataset):
    standard_names = ('x_velocity', 'y_velocity')

    @property
    def vector_vars(self):
        _vector_datasets = [(self._dset[dv].attrs.get('vector_component'), dv) for dv in self._dset.data_vars if
                            'vector_component' in self._dset[dv].attrs]
        # sort and return
        _vector_datasets.sort()
        return tuple([v[1] for v in _vector_datasets])

    def compute_magnitude(self, standard_name=None):
        """Computes the magnitude of the vector."""
        mag2 = None
        for ids, comp in enumerate(self.vector_vars):
            if mag2 is None:
                if comp in self._dset:
                    mag2 = self._dset[comp].pint.quantify() ** 2
            else:
                if comp in self:
                    mag2 += self[comp].pint.quantify() ** 2
        mag = np.sqrt(mag2).pint.dequantify(format=ureg.default_format)
        self._dset['magnitude'] = mag
        self._dset['magnitude'].attrs = mag.attrs
        if standard_name is None:
            # trying to determine a new standard name
            # TODO: compute new standard_name from standard_names of components: magnitude_of_[common_standard_name]
            component_standard_names = [self._dset[comp].attrs.get('standard_name') for comp in
                                        self.vector_vars]
            if all(component_standard_names):
                if all(['velocity' in c for c in component_standard_names]):
                    self['magnitude'].attrs['standard_name'] = 'magnitude_of_velocity'
                elif all(['displacement' in c for c in component_standard_names]):
                    self['magnitude'].attrs['standard_name'] = 'magnitude_of_displacement'
