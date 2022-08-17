"""H5Flow module: Wrapper for fluid dynamics data"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import Tuple, List
from typing import Union

import h5py
import numpy as np
import xarray as xr
from pandas import read_csv
from pint_xarray import unit_registry as ureg

from .accessory import SpecialDataset, register_special_dataset
from .h5file import H5File, H5Group, H5Dataset
from .. import config, conventions
from .._user import user_data_dir

# from ..conventions.custom import FluidStandardNameTable

logger = logging.getLogger(__package__)
DIM_NAMES = ('z', 'time', 'y', 'x')
DEVICE_ATTR_NAME = 'device'

H5File_layout_filename = Path.joinpath(user_data_dir, f'layout/H5File.hdf')
H5Flow_layout_filename = Path.joinpath(user_data_dir, f'layout/H5Flow.hdf')


def write_H5Flow_layout_file():
    """Write the H5File layout to <user_dir>/layout"""
    lay = conventions.layout.H5Layout.init_from(H5File_layout_filename, H5Flow_layout_filename)
    with lay.File(mode='r+') as h5lay:
        ds_x = h5lay.create_dataset('x', shape=(1,))
        ds_y = h5lay.create_dataset('y', shape=(1,))
        ds_z = h5lay.create_dataset('z', shape=(1,))
        ds_t = h5lay.create_dataset('time', shape=(1,))
        for ds in (ds_x, ds_y, ds_z):
            ds.attrs['__ndim__'] = (0, 1)
            ds.attrs['units'] = 'm'
        ds_x.attrs['standard_name'] = 'x_coordinate'
        ds_y.attrs['standard_name'] = 'y_coordinate'
        ds_z.attrs['standard_name'] = 'z_coordinate'
        ds_t.attrs['units'] = 's'
        ds_t.attrs['__ndim__'] = (0, 1)


# if not H5Flow_layout_filename.exists():
write_H5Flow_layout_file()


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


@dataclass(repr=False)
class Device:
    """Device Class. Expected use: A dataset has the attbute DEVICE_ATTR_NAME which s a
    referrs to a group entry in the HDF5 file."""

    name: str
    manufacturer: str = ''
    x: Union[xr.DataArray, Tuple[Union[float, int, np.ndarray], Union[str, Dict]]] = None
    y: Union[xr.DataArray, Tuple[Union[float, int, np.ndarray], Union[str, Dict]]] = None
    z: Union[xr.DataArray, Tuple[Union[float, int, np.ndarray], Union[str, Dict]]] = None
    additional_attributes: Dict = None

    def __repr__(self):
        return f'Device "{self.name}" from "{self.manufacturer}" @({self.x.data}, {self.y.data}, {self.z.data})' \
               f' [{self.x.units}])'

    def __post_init__(self):
        if self.additional_attributes is None:
            self.additional_attributes = {}

        def process_coord(coord, coord_name):
            """helper function to interprete coordinate data"""
            if coord is None:
                return None

            if isinstance(coord, xr.DataArray):
                return coord

            if isinstance(coord, tuple):
                if isinstance(coord[1], str):
                    return xr.DataArray(name=coord_name, data=coord[0], attrs=dict(units=coord[1]))
                else:
                    return xr.DataArray(name=coord_name, data=coord[0], attrs=coord[1])

        self.x = process_coord(self.x, 'x')
        self.y = process_coord(self.y, 'y')
        self.z = process_coord(self.z, 'z')

    @staticmethod
    def from_hdf_group(device_grp):
        """Creates a Device object from an HDF5 group"""
        name = device_grp.name.rsplit('/', 1)[1]
        additional_attributes = dict(device_grp.attrs.items())

        coords = dict()
        for coord_name in ('x', 'y', 'z'):
            if coord_name in device_grp:
                coords[coord_name] = xr.DataArray(name=coord_name, data=device_grp[coord_name][()],
                                                  attrs=device_grp[coord_name].attrs.items())
            else:
                coords[coord_name] = None

        return Device(name, additional_attributes.pop('manufacturer'), **coords, **additional_attributes)

    def to_hdf_group(self, grp: h5py.Group) -> h5py.Group:
        """writes data to an hdf group. strings are written to attributes of the group,
        dictionary entries"""
        device_grp = grp.create_group(self.name)
        device_grp.attrs['manufacturer'] = self.manufacturer
        for coord in (self.x, self.y, self.z):
            if coord is not None:
                coord.hdf.to_group(device_grp)
        for k, v in self.additional_attributes.items():
            device_grp.attrs[k] = v

        return device_grp


class H5FlowGroup(H5Group):
    """HDF5 Group specifically for flow data"""

    def create_dataset(self, *args, **kwargs):
        """Advanced dataset creation allowing for parameter device to pass during
        dataset creation"""
        attrs = kwargs.get('attrs', None)
        if attrs is None:
            _device = None
        else:
            _device = attrs.pop('device', None)
        device = kwargs.pop('device', _device)
        ds = super().create_dataset(*args, **kwargs)
        if device is not None:
            ds.attrs[DEVICE_ATTR_NAME] = device
        return ds

    def create_coordinates(self, x, y, z=0, time=0, coords_unit='m', time_unit='s'):
        """creating coordinate datasets"""
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


class H5FlowDataset(H5Dataset):
    """HDF5 Dataset specifically for flow data"""

    @property
    def device(self):
        """The device class referenced to this dataset"""
        if DEVICE_ATTR_NAME not in self.attrs:
            raise AttributeError(f'The dataset "{self.name}" has no attribute device, thus no reference to '
                                 f'a device in the HDF5 file exists!')
        device_grp = self.attrs[DEVICE_ATTR_NAME]
        return Device.from_hdf_group(device_grp)

    @device.setter
    def device(self, device: Union[str, h5py.Group, Device]):
        """Assigning a device to a dataset"""
        self.assign_device(device)

    def assign_device(self, device: Union[str, h5py.Group, Device]):
        """Assigning a device to a dataset"""
        if isinstance(device, str):
            if device in self:
                # setting the hdf goup reference
                self.attrs[DEVICE_ATTR_NAME] = self[device]
            elif device in self.rootparent:
                self.attrs[DEVICE_ATTR_NAME] = self.rootparent[device]
            else:
                raise AttributeError(f'No "device" found in hdf file found')
        elif isinstance(device, h5py.Group):
            # setting the hdf goup reference
            self.attrs[DEVICE_ATTR_NAME] = self.rootparent[device.name]
        elif isinstance(device, Device):
            if 'devices/' not in self.rootparent:
                self.rootparent.create_group('devices')
            grp_name = self.rootparent['devices']
            device_grp = device.to_hdf_group(grp_name)
            self.attrs[DEVICE_ATTR_NAME] = device_grp


class H5Flow(H5File, H5FlowGroup):
    """H5Flow File wrapper class"""

    def __init__(self, name: Path = None, mode='r', title=None, standard_name_table=None,
                 layout_filename: Path = H5Flow_layout_filename,
                 driver=None, libver=None, userblock_size=None,
                 swmr=False, rdcc_nslots=None, rdcc_nbytes=None, rdcc_w0=None,
                 track_order=None, fs_strategy=None, fs_persist=False, fs_threshold=1,
                 **kwds):
        if standard_name_table is None:
            standard_name_table = conventions.FluidStandardNameTable
        super().__init__(name, mode, title, standard_name_table,
                         layout_filename,
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
H5FlowGroup._h5ds = H5FlowDataset


@register_special_dataset("Vector", H5Group)
class VectorDataset(SpecialDataset):
    """Vector class with xarray.Dataset-like behaviour"""

    @property
    def vector_vars(self) -> Tuple:
        """Return the vector component variables"""
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


@register_special_dataset("VelocityVector", H5Group)
class VelocityDataset(VectorDataset):
    """Velocity vector class with xarray.Dataset-like behaviour.
    Expecting the group to have datasets with standard names x_velocity and y_velocity"""
    standard_names = ('x_velocity', 'y_velocity')

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
