"""H5PIV module: Wrapper for PIV data"""

import logging
import warnings
from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Callable, Tuple
from typing import Protocol, Any, Union, Dict, List

import numpy as np
from pint_xarray import unit_registry as ureg

from . import pivutils
from .accessory import register_special_dataset
from .h5flow import VectorDataset, H5FlowGroup, H5Flow, H5FlowDataset
from .. import config, _user
from ..conventions import layout as layoutconvention
from ..conventions.custom import PIVStandardNameTable
from ..x2hdf import piv

logger = logging.getLogger(__package__)


def next_std(sum_of_x, sum_of_x_squared, n, xnew, ddof):
    """computes the standard deviation after adding one more data point to an array.
    Avoids computing the standard deviation from the beginning of the array by using
    math, yeah :-)

    Parameters
    ----------
    sum_of_x : float
        The sum of the array without the new data point
    sum_of_x_squared : float
        The sum of the squared array without the new data point
    n : int
        Number of data points without the new data point
    xnew : float
        The new data point
    ddof : int, optional=0
        Means Delta Degrees of Freedom. See doc of numpy.std().
    """
    sum_of_x = sum_of_x + xnew
    sum_of_x_squared = sum_of_x_squared + xnew ** 2
    n = n + 1  # update n
    return sum_of_x, sum_of_x_squared, np.sqrt(1 / (n - ddof) * (sum_of_x_squared - 1 / n * (sum_of_x) ** 2))


def next_mean(mu, n_mu, new_val):
    """Computes the mean of an array after adding a new value to it

    Parameters
    ----------
    mu : float
        Mean value of the array before adding the new value
    n_mu : int
        Number of values in the array before adding the new value
    new_val : float
        The new value
    """
    return (mu * n_mu + new_val) / (n_mu + 1)


def _transpose_and_reshape_input(x, axis):
    return x.transpose([axis, *[ax for ax in range(x.ndim) if ax != axis]]).reshape(
        (x.shape[axis], x.size // x.shape[axis]))


def _transpose_and_reshape_back_to_original(x, orig_shape, axis):
    ndim = len(orig_shape)
    transpose_order = np.zeros(ndim).astype(int)
    transpose_order[axis] = 0
    k = 1
    for j in range(ndim):
        if j != axis:
            transpose_order[j] = k
            k += 1
    return x.reshape([orig_shape[axis], *[orig_shape[ax] for ax in range(ndim) if ax != axis]]).transpose(
        transpose_order)


def running_mean(x: np.ndarray, axis: int = 0) -> np.ndarray:
    """Computation of running mean"""
    if axis == -1:
        axis = x.ndim
    _x = _transpose_and_reshape_input(x, axis)
    xm = np.zeros_like(_x)
    m = _x[0, :]
    for i in range(1, _x.shape[0]):
        m = next_mean(m, i, _x[i, :])
        xm[i, :] = m
    return _transpose_and_reshape_back_to_original(xm, x.shape, axis)


def running_std(x: np.ndarray, axis: int, ddof: int = 0) -> np.ndarray:
    """Computation of running standard deviation"""
    if axis == -1:
        axis = x.ndim
    _x = _transpose_and_reshape_input(x, axis)
    x2 = _x ** 2
    std = np.zeros_like(_x)
    sum_of_x = np.sum(_x[0:ddof + 1], axis=0)
    sum_of_x_squared = np.sum(x2[0:ddof + 1], axis=0)
    std[0:ddof + 1] = np.nan
    for i in range(ddof + 1, _x.shape[0]):
        sum_of_x, sum_of_x_squared, std[i, :] = next_std(sum_of_x, sum_of_x_squared, i, _x[i, :], ddof=ddof)
    return _transpose_and_reshape_back_to_original(std, x.shape, axis)


def running_relative_standard_deviation(x, axis, ddof=0):
    """Computes the running relative standard deviation using the running
    mean as normalization."""
    return running_std(x, axis, ddof) / running_mean(x, axis)


H5Flow_layout_filename = Path.joinpath(_user.user_data_dir, f'layout/H5Flow.hdf')
H5PIV_layout_filename = Path.joinpath(_user.user_data_dir, f'layout/H5PIV.hdf')


def write_H5PIV_layout_file():
    """Write the H5File layout to <user_dir>/layout"""
    lay = layoutconvention.H5Layout.init_from(H5Flow_layout_filename, H5PIV_layout_filename)
    with lay.File(mode='r+') as h5lay:
        h5lay.attrs['title'] = '__The common name of the file that might ' \
                               'better explain it by a short string'

        # ds_vel = h5lay.create_dataset('x', shape=(1,))
        for n in ('x', 'y', 'z'):
            if n in h5lay:
                del h5lay[n]
        ds_x = h5lay.create_dataset('x', shape=(1,))
        ds_x.attrs['units'] = 'm'
        ds_x.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_x.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
        ds_x.attrs['standard_name'] = 'x_coordinate'

        # ds_vel = h5lay.create_dataset('y', shape=(1,))
        ds_y = h5lay.create_dataset('y', shape=(1,))
        ds_y.attrs['units'] = 'm'
        ds_y.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_y.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
        ds_y.attrs['standard_name'] = 'y_coordinate'

        ds_z = h5lay.create_dataset('z', shape=(1,))
        ds_z.attrs['units'] = 'm'
        ds_z.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_z.attrs['__ndim__'] = (0, 1)  # (nz, nt, ny, nx, nv)
        ds_z.attrs['standard_name'] = 'z_coordinate'

        if 'time' in h5lay:
            del h5lay['time']
        ds_t = h5lay.create_dataset('time', shape=(1,))
        ds_t.attrs['units'] = 's'
        ds_t.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_t.attrs['__ndim__'] = (0, 1)  # (nz, nt, ny, nx, nv)
        ds_t.attrs['standard_name'] = 'time'

        ds_ix = h5lay.create_dataset('ix', shape=(1,))
        ds_iy = h5lay.create_dataset('iy', shape=(1,))

        for ds, basename in zip((ds_ix, ds_iy), ('x', 'y')):
            ds.attrs['units'] = 'pixel'
            ds.attrs['__alternative_source_group__'] = 're:plane[0-9]'
            ds.attrs['__ndim__'] = 1
            ds.attrs['standard_name'] = f'{basename}_pixel_coordinate'

        ds_u = h5lay.create_dataset('u', shape=(1,))
        ds_u.attrs['units'] = 'm/s'
        ds_u.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_u.attrs['__ndim__'] = (2, 3, 4)  # (nz, nt, ny, nx, nv)
        ds_u.attrs['standard_name'] = 'x_velocity'

        ds_v = h5lay.create_dataset('v', shape=(1,))
        ds_v.attrs['units'] = 'm/s'
        ds_v.attrs['__alternative_source_group__'] = 're:plane[0-9]'
        ds_v.attrs['__ndim__'] = (2, 3, 4)  # 4: (nz, nt, ny, nx, nv)
        ds_v.attrs['standard_name'] = 'y_velocity'

        # piv parameters can be at root level or for each plane individually
        pivpargrp = h5lay.create_group('piv_parameters')
        pivpargrp.attrs['__alternative_source_group__'] = 're:plane[0-9]'


# if not H5Flow_layout_filename.exists():
write_H5PIV_layout_file()


class PIVMethod(Enum):
    """root attribute: data_source_type"""
    single_pass = 1
    multi_pass = 2
    multi_grid = 3


class PIVWindowFunction(Enum):
    """PIV Correlation Filter window type"""
    Uniform = 1
    Tukey = 2  # Tapered cosine
    Blackman = 3
    Hann = 4
    Hamming = 5
    Cosine = 6
    Gauss = 7
    LFC1 = 8
    LFC2 = 9
    LFC3 = 10


class PIVCorrelationMode(Enum):
    CrossCorrelation = 1
    PhaseOnlyCorrelation = 2
    MQD = 3
    DirectCossCorrelation = 4
    ErrorCorrelationFunction = 5


class PIVParamAdapter(Protocol):
    """Adapter Interface class"""

    def get(self, key: str, default: Any = None) -> Union[Any, None]:
        """Return the value associated with the key"""
        value = self.param_dict.get(key)
        if not value:
            return default
        return value


class PIVviewParameters:
    __slots__ = "preprocessing", "processing", "validation", "conversion"
    software_name = 'pivview'

    def __init__(self, param_dict: Dict) -> None:
        self.preprocessing = param_dict['---- PIV image pre-processing parameters ----']
        self.processing = param_dict['---- PIV processing parameters ----']
        self.validation = param_dict['---- PIV validation parameters ----']
        self.conversion = param_dict['---- PIV conversion parameters ----']

    def to_file(self, filename):
        """Write parameter to file"""
        raise NotImplementedError()

    def get(self, key: str, default: Any = None) -> Union[Any, None]:
        """Return the value associated with the key"""
        if key == 'method':
            return self.processing.get('View0_PIV_Eval_Method') + 1
        elif key == 'window_function':
            return self.processing.get('View0_PIV_Eval_CorrFilter_WindowType') + 1
        elif key == 'final_window_size':
            return self.processing.get('View0_PIV_Eval_SampleSize')
        elif key == 'overlap':
            return self.processing.get('View0_PIV_Eval_SampleStep')
        elif key == 'correlation_mode':
            return self.processing.get('View0_PIV_Eval_CorrelationMode') + 1
        return default


class PIVSoftware:
    """PIV-Software class"""

    def __init__(self, name, version, **kwargs):
        self._name = name
        if version is None:
            self._version = None
        else:
            self._version = str(version)
        self._attrs = kwargs

    @property
    def name(self) -> str:
        """returns software name"""
        return self._name

    @property
    def version(self) -> str:
        """returns software version"""
        return self._version

    def __getitem__(self, item):
        if item == 'name':
            return self._name
        if item == 'version':
            return self._version
        return self._attrs[item]

    def to_dict(self) -> dict:
        """exports the data to a dictionary"""
        _dict = self._attrs.copy()
        _dict.update(dict(name=self._name, version=self._version))
        return _dict


class PIVParameters:

    def __init__(self, piv_parameter):
        self.piv_parameter = piv_parameter

    @property
    def method(self):
        return PIVMethod(self.piv_parameter.get('method'))

    @property
    def final_window_size(self):
        return self.piv_parameter.get('final_window_size')

    @property
    def window_function(self) -> PIVWindowFunction:
        """cross correlation filter window type"""
        return PIVWindowFunction(self.piv_parameter.get('window_function'))

    @property
    def correlation_mode(self) -> PIVCorrelationMode:
        return PIVCorrelationMode(self.piv_parameter.get('correlation_mode'))


# class H5PIVLayout(H5FlowLayout):
#     """H5Layout for PIV data"""
#
#     def write(self) -> pathlib.Path:
#         """The layout file has the structure of a H5Flow file. This means
#         it has the required attributes, datasets and groups that are required
#         for a valid H5Flow file. For each application case this is of course
#         different. Such a file can be created and stored in the user directory
#         and will be used to check the completeness created H5Flow files
#
#         Dataset and group structure (attributes not shown):
#         /
#         /x     -> dim=(0, 1), m
#         /y     -> dim=(0, 1), m
#         /z     -> dim=(0, 1), m
#         /time  -> dim=(0, 1), s
#         """
#         super().write()
#         with h5py.File(self.filename, mode='r+') as h5:
#             # grsetup = h5.create_group(name='Setup')
#             # grpeq = grsetup.create_group(name='Equipment')
#             # grpeq.create_group('Camera')
#             # grpeq.create_group('Laser')
#             #
#             # _ = h5.create_group(name='Acquisition')
#             # h5.create_group(name='Acquisition/Raw')
#             # h5.create_group(name='Acquisition/Processed')
#             # h5.create_group(name='Acquisition/Calibration')
#
#             h5.attrs['title'] = '__The common name of the file that might ' \
#                                 'better explain it by a short string'
#
#             # ds_vel = h5.create_dataset('x', shape=(1,))
#             ds_vel = h5['x']
#             ds_vel.attrs['units'] = 'm'
#             ds_vel.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
#             ds_vel.attrs['standard_name'] = 'x_coordinate'
#
#             # ds_vel = h5.create_dataset('y', shape=(1,))
#             ds_vel = h5['y']
#             ds_vel.attrs['units'] = 'm'
#             ds_vel.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
#             ds_vel.attrs['standard_name'] = 'y_coordinate'
#
#             ds_ix = h5.create_dataset('ix', shape=(1,))
#             ds_iy = h5.create_dataset('iy', shape=(1,))
#
#             for ds in (ds_ix, ds_iy):
#                 ds.attrs['units'] = 'm'
#                 ds.attrs['__ndim__'] = (0, 1)
#                 ds_vel.attrs['standard_name'] = f'{ds_ix.name[1:]}_pixel_coordinate'
#
#             # ds_vel = h5.create_dataset('z', shape=(1,))
#             ds_vel = h5['z']
#             ds_vel.attrs['units'] = 'm'
#             ds_vel.attrs['__ndim__'] = (0, 1)  # (nz, nt, ny, nx, nv)
#             ds_vel.attrs['standard_name'] = 'z_coordinate'
#
#             ds_vel = h5.create_dataset('u', shape=(1,))
#             ds_vel.attrs['units'] = 'm/s'
#             ds_vel.attrs['__ndim__'] = (2, 3, 4)  # (nz, nt, ny, nx, nv)
#             ds_vel.attrs['standard_name'] = 'x_velocity'
#
#             ds_vel = h5.create_dataset('v', shape=(1,))
#             ds_vel.attrs['units'] = 'm/s'
#             ds_vel.attrs['__ndim__'] = (2, 3, 4)  # 4: (nz, nt, ny, nx, nv)
#             ds_vel.attrs['standard_name'] = 'y_velocity'
#
#         return self.filename


class H5PIVGroup(H5FlowGroup):
    """Group for H5PIV"""
    pass


class H5PIVDatset(H5FlowDataset):
    """Dataset for H5PIV"""
    pass


class H5PIV(H5Flow, H5PIVGroup, ABC):
    """H5PIV File class"""

    @property
    def ntimesteps(self):
        """returns the number of timestpes"""
        if 'time' in self:
            return self['time'].size
        raise KeyError(f'No dataset "time" in file. Cannot determine the number '
                       f'of timesteps')

    @property
    def nplanes(self):
        """returns the number of planes"""
        if 'z' in self:
            return self['z'].size
        raise KeyError(f'No dataset "z"" in file. Cannot determine the number '
                       f'of timesteps')

    @property
    def extent(self) -> Tuple[Tuple[float], Tuple[float]]:
        """
        Returns min and max coordinates of PIV volume

        Returns
        -------
        _min, _max : tuple
            (x,y,z)-coordinates at min and max PIV coordinates
        """
        _min, _max = list(), list()
        for n in ('x', 'y', 'z'):
            _min.append(np.nanmin(self[n][()]))
            _max.append(np.nanmax(self[n][()]))
        return tuple(_min), tuple(_max)

    @property
    def software(self) -> Union[PIVSoftware, None]:
        """Returns attribute 'software'"""
        if 'software' in self.attrs:
            _software = self.attrs.get('software')
        else:
            _software = self.attrs['pivview_parameters'].get('software')

        if isinstance(_software, dict):
            name = _software.pop('name', None)
            if name is None:
                warnings.warn(f'Software attribute cannot be interpreted: {name}')
                return None
            return PIVSoftware(name, _software.pop('version', None),
                               **_software)
        elif isinstance(_software, (tuple, list)):
            return PIVSoftware(*_software)
        # expecting a str
        return PIVSoftware(_software, version=None)

    @software.setter
    def software(self, software: Union[PIVSoftware, str], **kwargs):
        if isinstance(software, str):
            version = kwargs.pop('version', None)
            _software = PIVSoftware(software, version=version, **kwargs)
        elif isinstance(software, tuple):
            if len(software) > 3:
                _software = PIVSoftware(*software)
            else:
                raise ValueError('Only excepts tuples of length 2, e.g. ("softwarename", "version", extra_dict)')
        else:
            _software = software
        self.attrs['software'] = _software.to_dict()

    def get_parameters(self, iz: int = None) -> PIVParameters:
        """Retruns the PIVParameter class of the respective software (if identified)

        if pivview is identified:
            Returns an instance of PivViewParFle. It looks for the parameter dictionary depending on the
            data structure:
            - z-coordinate is 0D: It is a PIV plane and piv_parameter dictionary is stored in the root attributes
            - z-coordinate is 1D: There is a piv_parameter group at root level with a parameter dictionary for each plane

            As HDF files cannot store dictionares, the parameters are stred as a string-representation of a dictionary
            (json.dumps()
        """
        software = self.software

        def _get_parameter_dict():
            if 'piv_parameters' in self.attrs:  # at root level --> valid for all z
                return [self.attrs['piv_parameters'], ]
            else:
                plane_candidates = sorted(list([k for k in self.groups if 'plane' in k]))
                return [plane_candidates.attrs['piv_parameters'] for pc in plane_candidates]

        piv_parameter_list = _get_parameter_dict()
        if len(piv_parameter_list) > 1 and iz is None:
            raise KeyError('You must specify the plane.')
        else:
            iz = 0

        for key, value in AV_PIV_PARAMETER.items():
            if software.name in key:
                return PIVParameters(value(piv_parameter_list[iz]))
        raise NotImplementedError(f'No PIV Parameter class for software {software.name}.')

    @property
    def resolution(self):
        """number of vectors per area [1/<real unit>^2]"""

        def _get_min(ds_name):
            if 'min' in self[ds_name].attrs:
                coord_unit = self[ds_name].unit
                _min = self[ds_name].attrs['min'] * coord_unit
            else:
                _min = self[ds_name][:].min()
            return _min

        def _get_max(ds_name):
            if 'max' in self[ds_name].attrs:
                coord_unit = self[ds_name].unit
                _max = self[ds_name].attrs['max'] * coord_unit
            else:
                _max = self[ds_name][:].max()
            return _max

        xmin = _get_min('x')
        ymin = _get_min('y')
        zmin = _get_min('z')

        xmax = _get_max('x')
        ymax = _get_max('y')
        zmax = _get_max('z')

        area_xy = (xmax - xmin) * (ymax - ymin)

        if zmax == zmin:
            volume = area_xy
        else:
            volume = area_xy * (zmax - zmin)

        nz = self['x'].shape[0]
        ny = self['x'].shape[2]
        nx = self['x'].shape[3]

        res_xy = nx * ny / area_xy
        res_xyz = nx * ny * nz / volume

        return res_xy, res_xyz

    def compute_uncertainty(self, displacement_dataset: VectorDataset, method: Callable, *args, **kwargs):
        """computes the PIV uncertainty based on the displacement vector and method passed"""
        return displacement_dataset(method, *args, **kwargs)

    def special_inspect(self, silent: bool = False) -> int:
        """Conditional inspection"""
        n_issues = 0
        if 'z' in self and 'time' in self:
            if self["z"].ndim == 0 and self["time"].ndim == 1:
                expected_base_shape = (self["time"].shape[0], self["y"].shape[0], self["x"].shape[0])
            elif self["z"].ndim == 1 and self["time"].ndim == 1:
                expected_base_shape = (self["z"].shape[0], self["time"].shape[0],
                                       self["y"].shape[0], self["x"].shape[0])
            elif self["z"].ndim == 1 and self["time"].ndim == 0:
                expected_base_shape = (self["z"].shape[0], self["y"].shape[0], self["x"].shape[0])
            else:
                expected_base_shape = (self["y"].shape[0], self["x"].shape[0])
            if not self["u"].shape == expected_base_shape:
                n_issues += 1
        return n_issues

    def get_conversion_factor(self):
        """returns conversion factor in [pix/physical_unit]"""
        dx = self['x'][0, 0, 0, :].max() - self['x'][0, 0, 0, :].min()
        dy = self['y'][0, 0, :, 0].max() - self['y'][0, 0, :, 0].min()
        par = self.get_piv_parameters()
        image_size = eval(par['---- PIV processing parameters ----']['View0_PIV_Image_Size'])
        image_diagonal = np.sqrt(image_size[0] ** 2 + image_size[1] ** 2) * ureg('pixel')
        object_diagonal = np.sqrt(dx ** 2 + dy ** 2)
        return image_diagonal / object_diagonal

    def get_magnification(self):
        raise NotImplementedError()

    def get_pulse_delay(self, iz: int = 0):
        par = self.get_piv_parameters(iz)
        if par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'milliseconds':
            return par.get_pulse_delay() * ureg.ms
        elif par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'microseconds':
            return par.get_pulse_delay() * ureg.us
        elif par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'nano':
            return par.get_pulse_delay() * ureg.ns
        elif par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'minutes':
            return par.get_pulse_delay() * ureg.m
        elif par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'hours':
            return par.get_pulse_delay() * ureg.h
        elif par['conversion parameters']['View0_PIV_Conv_PulseDelayUnits'] == 'seconds':
            return par.get_pulse_delay() * ureg.s
        else:
            raise ValueError('Cannot evaluate pulse delay unit '
                             f'"{self["conversion parameters"]["View0_PIV_Conv_PulseDelayUnits"]}"')

    def get_piv_eval_method_id(self, iz: int = 0) -> int:
        """return PIV evaluation method id as integer (0: single Pass, 1: multi Pass, 2:multi Grid)"""
        par = self.get_piv_parameters(iz)
        return int(par['PIV processing parameters']['View0_PIV_Eval_Method'])

    def get_piv_eval_method(self, iz: int = 0) -> str:
        """return PIV evaluation method as string (single Pass, multi Pass, multi Grid)"""
        eval_id = self.get_piv_eval_method_id(iz)
        if eval_id == 0:
            return 'single pass'
        if eval_id == 1:
            return 'multi pass'
        if eval_id == 2:
            return 'multi grid'
        return 'unknown'

    def get_piv_sample_step(self, iz: int = 0) -> List[int]:
        par = self.get_piv_parameters(iz)
        return eval(par['PIV processing parameters']['View0_PIV_Eval_SampleStep'])

    def __init__(self, name=None, mode="r+", title=None, standard_name_table=None,
                 layout_filename: Path = H5PIV_layout_filename,
                 software=None, run_layout_check=False, **kwargs):
        """
        name : str, optional=None
            Name of the file on disk, or file-like object.
            If None, a file is created in user tmp folder
        mode: str, optional='r+'
            r        Readonly, file must exist (default)
            r+       Read/write, file must exist
            w        Create file, truncate if exists
            w- or x  Create file, fail if exists
            a        Read/write if exists, create otherwise
        software : str
            PIV software used
        run_layout_check : bool, option=True
            Checks layout requirements for H5PIV (must have certain datasets
            and groups and attributes)
        kwargs : dict, optional={}
            Optional keyword arguments that are passed to h5py.File.__init__()

        Returns
        -------
        None

        """
        if standard_name_table is None:
            standard_name_table = PIVStandardNameTable
        super(H5PIV, self).__init__(name=name, mode=mode, title=title,
                                    standard_name_table=standard_name_table,
                                    layout_filename=layout_filename,
                                    **kwargs)
        if software is not None:
            if isinstance(software, str):
                if mode in ('r+', 'w'):
                    self.software = software
                    logger.debug(f'Software name is set to {software} for the dataset')
        if run_layout_check and mode != 'w':  # only makes sense if file exists already
            self.layout_check()

    def is_timestep(self):
        if config.piv_file_type_attr_name in self:
            return self.attrs[config.piv_file_type_attr_name] == config.piv_file_types['timestep']
        else:
            raise AttributeError(f'HDF file has no attribute {config.piv_file_type_attr_name}')

    def is_plane(self):
        if config.piv_file_type_attr_name in self:
            return self.attrs[config.piv_file_type_attr_name] == config.piv_file_types['plane']
        else:
            raise AttributeError(f'HDF file has no attribute {config.piv_file_type_attr_name}')

    # def is_multiplane(self):
    #     """returns """
    #     if config.piv_file_type_attr_name in self:
    #         return self.attrs[config.piv_file_type_attr_name] == config.piv_file_types['multi_plane']
    #     else:
    #         raise AttributeError(f'HDF file has no attribute {config.piv_file_type_attr_name}')

    def add_bg_image(self, bg_img_file1, bg_img_file2=None, overwrite=False):
        if bg_img_file2:
            self.create_dataset_from_image((bg_img_file1, bg_img_file2), 'background_image', units='pixel',
                                           long_name='Background images for snapshot A (0) and B (1)'
                                                     ' respectively.', overwrite=overwrite)
        else:
            self.create_dataset_from_image(bg_img_file1, 'background_image', units='pixel',
                                           long_name='Background images for both snapshots A and B.',
                                           overwrite=overwrite)

    def compute_dwdz(self, name='dwdz', overwrite=False,
                     long_name=None):
        """
        Computes velocity gradient dw/dz from dudx and dvdy. Only
        valid fro incompresisble flows! Datasets dudx and dvdy are
        detected in the current group by their standard_names. Thus,
        if not set, an error will be raised.

        Parameters
        ----------
        name : str, optional='dwdz'
            Name to use for velocity gradient dw/dz
        overwrite : bool, optional=False
            Whether to overwrite an existing dataset with name
        long_name : str, optional='Velocity Gradient dw/dz'
            Description used for hdf dataset.

        Returns
        -------
        ds : hdf dataset
            created dataset

        """
        dudx = self.get_dataset_by_standard_name('x_derivative_of_x_velocity')
        dvdy = self.get_dataset_by_standard_name('y_derivative_of_y_velocity')
        if dudx is None:
            raise KeyError(f'Could not find a dataset with standard name "x_derivative_of_x_velocity" in {self.name}')
        if dvdy is None:
            raise KeyError(f'Could not find a dataset with standard name "y_derivative_of_y_velocity" in {self.name}')
        if name in self and not overwrite:
            # let h5py raise the error:
            self.create_dataset(name, shape=(1,))
        dwdz = -dudx[:].pint.quantify() - dvdy[:].pint.quantify()
        ds = self.create_dataset(name=name, standard_name='z_derivative_of_z_velocity',
                                 long_name=long_name,
                                 data=dwdz, overwrite=overwrite)
        return ds

    def compute_vdp(self, name='vdp', flag_valid=1, flag_masked=(2, 10),
                    overwrite=False):
        """creates vdp for each xy coordinate for all it and iz
        Parameters
        ----------
        name : str
            Name to use for dataset
        flag_valid : int, optional=1
            flag defining a valid vector
        flag_masked : tuple
            Flags defining masked out vectors
        overwrite : bool, optional=False
            Whether to overwrite an existing dataset with given name

        Returns
        -------
        ds : Dataset
            created dataset

        """
        piv_flags = self['piv_flags'][:, :, :, :]
        nz, nt = piv_flags.shape[0], piv_flags.shape[1]
        vdp_data = np.zeros(shape=(nz, nt, 1, 1))
        for iz in range(nz):
            for it in range(nt):
                vdp_data[iz, it, 0, 0] = pivutils.vdp(piv_flags=piv_flags[iz, it, :, :], flag_valid=flag_valid,
                                                      flag_masked=flag_masked, abs=False)
        description = 'valid detection probability'
        comment = 'The absolute or relative number of valid vectors of the result array without taking masked ' \
                  f'entries into account. The following flags were used for processing. Valid={flag_valid}, ' \
                  f'masked={flag_masked}. Calculation used: n_valid = (n_nonmasked-n_invalid)/n_nonmasked. ' \
                  f'Flag translation was performed with current version ({self.version}) and PIV software {self.software}.'
        ds = self.create_dataset(name=name, data=vdp_data, units=' ', overwrite=overwrite,
                                 long_name=description, attrs={'comment': comment},
                                 attach_scale=('z', 'time'))
        return ds

    def _compute_running_statistics(self, method, grp_name, grp_long_name, dataset, dataset_long_name, overwrite,
                                    **kwargs):
        """statistic_measure is 'mean' or 'std'. More infor see compute_running_mean and compute_running_std

        Return
        ------
        rds : H5Dataset
            The created dataset
        """
        if isinstance(dataset, str):
            dataset = self[dataset]

        if self.mode not in ('r+', 'w', 'a'):
            logger.error("File not in r+ mode!")

        if dataset.name[0] == '/':
            ds_name = dataset.name[1:]
        else:
            ds_name = dataset.name

        method_dataset_name = f"/{grp_name}/{ds_name}"

        # calculate or skip
        dataset_units = dataset.units
        if method_dataset_name not in self or overwrite:
            _value = method(dataset[:].values, **kwargs)
            write_to_hdf = True
        else:
            write_to_hdf = False
            logger.info(f'Running {method.__name__} for {dataset.name} was not '
                        f'computed because it already exists. Set \'recompute=True\''
                        f' do re-calculate the values.')

        # if calculated, then write:
        if write_to_hdf:
            if grp_name not in self:
                g = self.create_group(grp_name, long_name=grp_long_name)
            else:
                g = self[grp_name]

            compression, compression_opts = config.hdf_compression, config.hdf_compression_opts

            # create dataset and attributes with it
            rds = g.create_dataset(name=ds_name, data=_value, units=dataset_units,
                                   long_name=dataset_long_name, overwrite=overwrite,
                                   compression=compression,
                                   compression_opts=compression_opts)

            # attach scales according to input dataset:
            for i in range(4):
                if len(dataset.dims[i]):
                    rds.dims[i].attach_scale(dataset.dims[i][0])
            return rds
        return self[method_dataset_name]

    def compute_running_mean(self, dataset, overwrite=False):
        """
        Computes the running mean and stores it in
        group /post/running_mean/ under the same variable name

        Parameters
        ----------
        dataset : str
            Dataset name to compute running mean on. Default is "/velocity".
        overwrite : bool, optional=False
            Recomputes the data if already exists. Default is False.

        Returns
        -------
        ds : H5Dataset
            The created dataset
        """
        grp_desc = 'Running mean of PIV datasets. This is typically used to judge ' \
                   'convergence of PIV phase-averaged recordings'
        if isinstance(dataset, str):
            dataset_desc = f'Running mean of {dataset}'
        else:
            dataset_desc = f'Running mean of {dataset.name}'
        return self._compute_running_statistics(pivutils.running_mean,
                                                grp_name='post/running_mean',
                                                grp_long_name=grp_desc,
                                                dataset=dataset,
                                                dataset_long_name=dataset_desc,
                                                overwrite=overwrite,
                                                axis=1)

    def compute_running_std(self, dataset='/velocity', overwrite=False):
        """
        Computes the running std and stores it in
        group /post/running_std/ under the same variable name

        Parameters
        ----------
        dataset : str, optional='/velocity'
            Dataset name to compute running mean on. Default is "/velocity".
        overwrite : bool, optional=False
            Recomputes the data if already exists. Default is False.

        Returns
        -------
        ds : H5Dataset
            The created dataset
        """
        grp_desc = 'Running standard deviation of PIV datasets. This is typically used to judge ' \
                   'convergence of PIV phase-averaged recordings'
        if isinstance(dataset, str):
            dataset_desc = f'Running standard deviation of {dataset}'
        else:
            dataset_desc = f'Running standard deviation of {dataset.name}'
        return self._compute_running_statistics(pivutils.running_std,
                                                grp_name='post/running_std',
                                                grp_long_name=grp_desc,
                                                dataset=dataset,
                                                dataset_long_name=dataset_desc,
                                                overwrite=overwrite,
                                                ddof=2,
                                                axis=1)

    def get_image_files(self, iz, it, split_image, cam_rel_dir='../Cam1', img_suffix='.b16'):
        """Returns the file path corresponding to snapshot it in plane iz.
        For this, the root attribute plane_directory (for snapshot and planes) or
        plane_directories (for cases) respectively must be available. At this stage
        it is assumed, that the relative location of the image folder is at ../Cam1.
        This can be changed via the argument cam_rel_dir"""
        # if this file is a snapshot or plane HDF file, plane folder information is stored at
        # root level:
        warnings.warn('Assumes that cam folder is located in plane directory and is called "Cam1"'
                      'and file extension is *.b16!')
        if not iz < self['velocity'].shape[1]:
            raise ValueError('Requested plane index larger than available planes')

        if 'plane_directory' in self.attrs:
            plane_dir = Path(self.attrs['plane_directory'])
        elif 'plane_directories' in self.attrs:
            plane_dir = Path(self.attrs['plane_directories'][iz])
        img_list = sorted(Path.joinpath(plane_dir, cam_rel_dir).glob(f'*{img_suffix}'))
        if split_image:
            return img_list[it], img_list[it]
        return img_list[2 * it], img_list[2 * it + 1]

    def to_vtk(self, vtk_filename: Path = None) -> Path:
        """generates a vtk file with time-averaged data"""
        if 'timeAverages' not in self:
            raise ValueError('The group "timeAverages" does not exist. Cannot write VTK file!')
        filename = Path(self.filename)
        if vtk_filename is None:
            _vtk_filename = Path.joinpath(filename.parent, filename.stem)
        else:
            _vtk_filename = Path(vtk_filename)
            if _vtk_filename.suffix != '':
                _vtk_filename = Path.joinpath(vtk_filename.parent, vtk_filename.stem)
            else:
                _vtk_filename = vtk_filename
        data = piv.vtk_utils.get_time_average_data_from_piv_case(self.filename)
        _, vtk_path = piv.vtk_utils.result_3D_to_vtk(
            data, target_filename=_vtk_filename)
        return vtk_path


H5PIVGroup._h5grp = H5PIVGroup
H5PIVGroup._h5ds = H5PIVDatset


@register_special_dataset("DisplacementVector", H5PIVGroup)
class PIVDisplacementDataset(VectorDataset):
    """Displacement vector class with xarray.Dataset-like behaviour.
    Expecting the group to have datasets with standard names x_displacement and y_displacement"""
    standard_names = ('x_displacement', 'y_displacement')

    def compute_uncertainty(self, method: Callable, *args, **kwargs):
        """computes the uncertainty using the passed method"""
        return method(self, *args, **kwargs)


AV_PIV_PARAMETER = {'pivview': PIVviewParameters, }
