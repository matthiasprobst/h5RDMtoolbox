import abc
import os
import pathlib
from typing import List, Union, Dict
from typing import Tuple

import h5py
import numpy as np

from ._config import DEFAULT_CONFIGURATION
from ...utils import generate_temporary_filename

PIV_PARAMETER_GRP_NAME = 'piv_parameters'

def scan_for_timeseries_nc_files(folder_path: pathlib.Path, suffix: str) -> List[pathlib.Path]:
    """
    Scans for nc files (extension '.nc') in folder. Omits all files that do not end with numeric character [0-9]
    or end with [0-9] and a single character.
    """
    list_of_files = sorted(folder_path.glob(f'*[0-9]?{suffix}'))
    if len(list_of_files) > 0:
        return list_of_files
    else:
        return sorted(folder_path.glob(f'*[0-9]{suffix}'))


class PIVParameterInterface(abc.ABC):
    """Abstract PIV Parmeter Interface"""
    __slots__ = 'param_dict'
    suffix = '.par'

    def __init__(self, filename):
        self.filename = filename
        self.param_dict = dict()

    @staticmethod
    @abc.abstractmethod
    def from_dir(dirname):
        """reads parameter from dirname"""

    @abc.abstractmethod
    def save(self, filename: pathlib.Path):
        """Save to original file format"""

    def to_dict(self) -> Dict:
        """Convert to a ditionary"""
        return self.param_dict

    def to_hdf(self, grp: h5py.Group) -> h5py.Group:
        """Recursively walk thorugh data dictionary and write content to HDF group"""

        def _to_grp(_dict, _grp):
            for k, v in _dict.items():
                if isinstance(v, dict):
                    _grp = _to_grp(v, _grp.create_group(k))
                else:
                    _grp.attrs[k] = v
            return _grp

        return _to_grp(self.param_dict, grp)


class PIVFile(abc.ABC):
    """Basic Particle Image Velocimetry File"""
    suffix: str = ''
    parameter = PIVParameterInterface

    def __init__(self, filename: pathlib.Path, parameter_filename: Union[None, pathlib.Path] = None):
        _filename = pathlib.Path(filename)
        if not filename.is_file:
            raise TypeError(f'Snapshot file path is not a file: {_filename}.')
        if self.suffix != '':
            if filename.suffix != self.suffix:
                raise NameError(f'Expecting suffix {self.suffix}, not {_filename.suffix}')
        self.filename = _filename
        if parameter_filename is None:
            self._parameter = self.parameter.from_dir(filename.parent)
        else:
            self._parameter = self.parameter(parameter_filename)

    @abc.abstractmethod
    def read(self, config, recording_time: float, build_coord_datasets=True) -> Tuple[Dict, Dict, Dict]:
        """Read data from file.
        Except data, root_attr, variable_attr"""
        pass

    def write_parameters(self, param_grp: h5py.Group):
        """Write piv parameters to an opened and existing param_grp"""
        return self._parameter.to_hdf(param_grp)

    @abc.abstractmethod
    def to_hdf(self, hdf_filename: pathlib.Path, config: Dict, recording_time: float) -> pathlib.Path:
        """converts the snapshot into an HDF file"""


class PIVConverter(abc.ABC):
    """Abstrct converter class"""

    @abc.abstractmethod
    def to_hdf(self, hdf_filename, config) -> pathlib.Path:
        """conversion method"""


class PIVSnapshot(PIVConverter):
    """Interface class"""

    def __init__(self, piv_file: PIVFile, recording_time: float):
        if not isinstance(piv_file, PIVFile):
            raise TypeError(f'Expecting type {PIVFile.__class__}, not type {type(piv_file)}')
        self.piv_file = piv_file
        self.recording_time = recording_time

    def to_hdf(self, hdf_filename=None, config=None) -> pathlib.Path:
        """converts the snapshot into an HDF file"""
        if config is None:
            config = DEFAULT_CONFIGURATION
        else:
            if not isinstance(config, Dict):
                raise TypeError(f'Configuration must a dictionary, not {type(config)}')
        if hdf_filename is None:
            hdf_filename = self.piv_file.filename.parent / f'{self.piv_file.filename.stem}.hdf'
        return self.piv_file.to_hdf(hdf_filename, config, self.recording_time)

    @staticmethod
    def from_pivview(nc_filename: pathlib.Path, recording_time: float):
        from .pivview import PIVViewNcFile
        return PIVSnapshot(PIVViewNcFile(nc_filename), recording_time)


class PIVPlane(PIVConverter):
    """Interface class"""

    __slots__ = 'list_of_piv_file', 'time_vector'
    plane_coord_order = ('time', 'y', 'x')

    def __init__(self, list_of_piv_file: List[PIVFile],
                 recording_time_or_frequency: Union[float, np.ndarray, List[float]]):
        if not isinstance(list_of_piv_file, (tuple, list)):
            raise TypeError(f'Expecting a list of {PIVFile.__class__} objects but got {type(list_of_piv_file)}')
        if not all([isinstance(piv_file, PIVFile) for piv_file in list_of_piv_file]):
            for piv_file in list_of_piv_file:
                if not isinstance(piv_file, PIVFile):
                    raise TypeError(
                        f'Expecting type {PIVFile.__class__} for each entry, but one entry is of type {type(piv_file)}')
        self.list_of_piv_file = list_of_piv_file
        n = len(list_of_piv_file)
        if isinstance(recording_time_or_frequency, (float, int)):  # a frequency is passed in [Hz]
            # build time vector
            if recording_time_or_frequency == 0.:
                time_vector = np.zeros(n)
            else:
                time_vector = np.arange(0, n / recording_time_or_frequency, 1 / recording_time_or_frequency)
        else:
            time_vector = recording_time_or_frequency
        self.time_vector = time_vector

    @staticmethod
    def from_plane_folder(plane_directory: pathlib.Path,
                          recording_time_or_frequency: Union[float, np.ndarray, List[float]],
                          cls: PIVFile, n: int = -1):
        """initializes a PIV Plane from a piv plane folder"""
        found_nc_files = scan_for_timeseries_nc_files(plane_directory, cls.suffix)
        if n == -1:
            n = len(found_nc_files)
        if n == 0:
            raise ValueError('Number of found nc files is zero. Something went wrong. Please check '
                             f'the content of {plane_directory}')
        return PIVPlane([cls(nc) for nc in found_nc_files], recording_time_or_frequency)

    def to_hdf(self, hdf_filename: pathlib.Path = None, config: Dict = None) -> pathlib.Path:
        """converts the snapshot into an HDF file"""
        if config is None:
            config = DEFAULT_CONFIGURATION
        else:
            if not isinstance(config, Dict):
                raise TypeError(f'Configuration must a dictionary, not {type(config)}')
        if hdf_filename is None:
            hdf_filename = self.list_of_piv_file[0].filename.parent / f'{self.list_of_piv_file[0].filename.parent}.hdf'
        # get data from first snapshot to prepare the HDF5 file
        data, root_attr, variable_attr = self.list_of_piv_file[0].read(config, self.time_vector[0])
        mandatory_keys = ('x', 'y', 'z', 'ix', 'iy', 'u', 'v')
        for mkey in mandatory_keys:
            if mkey not in data.keys():
                raise KeyError(f'Mandatory key {mkey} not provided.')
        nt, ny, nx = self.time_vector.size, data['y'].size, data['x'].size
        _shape = dict(time=nt, y=ny, x=nx)
        dataset_shape = tuple([_shape[k] for k in self.plane_coord_order])
        _chunk = [_shape[n] for n in self.plane_coord_order]
        _chunk[self.plane_coord_order.index('time')] = 1
        dataset_chunk = tuple(_chunk)
        iy_idim = self.plane_coord_order.index('y')
        ix_idim = self.plane_coord_order.index('x')
        compression = config['compression']
        compression_opts = config['compression_opts']
        with h5py.File(hdf_filename, 'w') as h5main:
            h5main.attrs['title'] = 'piv plane data'
            for ak, av in root_attr.items():
                h5main.attrs[ak] = av
            self.list_of_piv_file[0].write_parameters(h5main.create_group(PIV_PARAMETER_GRP_NAME))
            h5main.create_dataset('x', data=data['x'], maxshape=nx)
            h5main.create_dataset('ix', data=data['ix'], maxshape=nx)
            h5main.create_dataset('y', data=data['y'], maxshape=nx)
            h5main.create_dataset('iy', data=data['iy'], maxshape=nx)
            h5main.create_dataset('z', data=data['z'])
            h5main.create_dataset('time', data=self.time_vector)
            for varkey in ('x', 'y', 'time'):
                h5main[varkey].make_scale()
                for ak, av in variable_attr[varkey].items():
                    h5main[varkey].attrs[ak] = av
            for varkey in ('ix', 'iy', 'z'):
                for ak, av in variable_attr[varkey].items():
                    h5main[varkey].attrs[ak] = av
            dataset_keys = []  # fill with dataset names that are not coordinates.
            for varkey, vardata in data.items():
                if varkey not in ('x', 'y', 'ix', 'iy', 'z', 'time'):
                    dataset_keys.append(varkey)
                    ds = h5main.create_dataset(varkey, shape=dataset_shape,
                                               maxshape=dataset_shape,
                                               chunks=dataset_chunk,
                                               compression=compression,
                                               compression_opts=compression_opts)
                    for idim, coordname in enumerate(self.plane_coord_order):
                        ds.dims[idim].attach_scale(h5main[coordname])
                    ds.dims[iy_idim].attach_scale(h5main['iy'])
                    ds.dims[ix_idim].attach_scale(h5main['ix'])
                    ds.attrs['COORDINATES'] = ['z', ]
                    ds[0, ...] = vardata[...]
                    # write attributes to datasets
                    for ak, av in variable_attr[varkey].items():
                        ds.attrs[ak] = av

            # write all other dataset to file:
            for (ifile, piv_file), t in zip(enumerate(self.list_of_piv_file[1:]), self.time_vector[1:]):
                data, _, _ = piv_file.read(config, t)
                for varkey in dataset_keys:
                    h5main[varkey][ifile + 1, ...] = data[varkey][...]
        return hdf_filename


class PIVMultiPlane(PIVConverter):
    """Interface class"""
    __slots__ = 'list_of_piv_folder'
    plane_coord_order = ('z', 'time', 'y', 'x')

    def __init__(self, list_of_piv_folder: List[List[PIVFile]]):
        if not isinstance(list_of_piv_folder, (tuple, list)):
            raise TypeError(
                f'Expecting a lists of list of {PIVFile.__class__} objects but got {type(list_of_piv_folder)}')
        self.list_of_piv_folder = list_of_piv_folder

    @staticmethod
    def merge_planes(hdf_filenames: List[pathlib.Path], target_hdf_filename: pathlib.Path,
                     rtol=1.e-5, atol=1.e-8, fill_time_vec_differences: bool = False):
        """merges multiple piv plane hdf files together

        rtol: float=1.e-5
            Relative tolerance used in np.allclose() to check if time vectors are equal
        atol: float=1.e-8
            Absolute tolerance used in np.allclose() to check if time vectors are equal
        fill_time_vec_differences:bool=False
            If time vectors have different length but are close, the datasets are filled with NaNs
        """
        nt_list = []
        t_list = []
        x_data = []
        y_data = []
        z_data = []
        dim_names = []
        for hdf_file in hdf_filenames:
            with h5py.File(hdf_file) as h5plane:
                nt_list.append(h5plane['time'].size)
                t_list.append(h5plane['time'][()])
                x_data.append(h5plane['x'][:])
                y_data.append(h5plane['y'][:])
                z_data.append(h5plane['z'][()])
                dim_names.append([d[0].name for d in h5plane['u'].dims])
        if any([dim_names[0] != d for d in dim_names]):
            raise RuntimeError('Inconsistent dimension names. All planes must have same dimension names'
                               'for all datasets.')
        # check compliance of planes:
        # they only can be merged if x and y data is equal but z is different:
        if not np.all([np.array_equal(x_data[0], x) for x in x_data[1:]]):
            raise ValueError('x coordinates of planes are differnt. Cannot merge.')
        if not np.all([np.array_equal(y_data[0], y) for y in y_data[1:]]):
            raise ValueError('y coordinates of planes are differnt. Cannot merge.')
        if np.any([z_data[0] == z for z in z_data[1:]]):
            raise ValueError(f'z coordinates must be different in order to merge the planes: {z_data}')

        # now check if the time vectors have the same length.
        equal_length = np.all([nt_list[0] == nt for nt in nt_list[1:]])

        if not equal_length:
            # you may want to force a merge:
            if fill_time_vec_differences:
                nt_min = min(nt_list)
                if np.all([np.allclose(t_list[0][0:nt_min], t[0:nt_min], rtol=rtol, atol=atol) for t in t_list[1:]]):
                    return PIVMultiPlane._merge_planes_equal_time_vectors(hdf_filenames, target_hdf_filename,
                                                                          nt=max(nt_list))
            return PIVMultiPlane._merge_planes_unequal_time_vectors(hdf_filenames, target_hdf_filename)
        else:
            # same length but still time vectors could be different
            if np.all([np.allclose(t_list[0], t, rtol=rtol, atol=atol) for t in t_list[1:]]):
                # identical time vectors
                return PIVMultiPlane._merge_planes_equal_time_vectors(hdf_filenames, target_hdf_filename)
            else:
                # write datasets into separate planes
                return PIVMultiPlane._merge_planes_unequal_time_vectors(hdf_filenames, target_hdf_filename)
            # then if they do have the same length, they must have the same entries in order to merged the datasets

    @staticmethod
    def _merge_planes_equal_time_vectors(hdf_filenames: List[pathlib.Path],
                                         target_hdf_filename: pathlib.Path,
                                         nt: int = None):
        nz = len(hdf_filenames)
        with h5py.File(hdf_filenames[0]) as h5plane:
            if nt is None:
                nt = h5plane['time'].size
            ny = h5plane['y'].size
            nx = h5plane['x'].size
            dim_names = [os.path.basename(d[0].name) for d in h5plane['u'].dims]
            plane_coord_order = PIVMultiPlane.plane_coord_order
            shape_dict = {'time': nt, 'x': nx, 'y': ny}
            _ds_shape_list = [shape_dict[n] for n in dim_names]
            ix = plane_coord_order.index('x')
            iy = plane_coord_order.index('y')
            if abs(ix - iy) > 1:
                raise ValueError('Invalid plane coord position. x and y must be next to eachother.')
            iz = plane_coord_order.index('z')
            it = plane_coord_order.index('time')
            if iz == 0 and it == 1:
                ds_shape = (nz, nt, ny, nx)
                ds_chunk = (1, 1, ny, nx)
            elif iz == 1 and it == 0:
                ds_shape = (nt, nz, ny, nx)
                ds_chunk = (1, 1, ny, nx)
            else:
                raise NotImplementedError('Cannot work with that shape...')

                # z before time:
                # ds_shape = (nz, nt, ny, nx)
            # shape = {'time': nt, 'x': nx, 'y': ny}
            coord_names = ('x', 'y', 'time', 'z', 'ix', 'iy')
            dataset_names = [k for k, v in h5plane.items() if isinstance(v, h5py.Dataset) and k not in coord_names]

            compression = h5plane['u'].compression
            compression_opts = h5plane['u'].compression_opts

        with h5py.File(target_hdf_filename, 'w') as h5main:
            # h5main.attrs['software'] = PIVMultiPlane.software_name
            h5main.attrs['title'] = 'piv snapshot data'
            ds_x = h5main.create_dataset('x', shape=(nx,))
            ds_x.make_scale()
            ds_y = h5main.create_dataset('y', shape=(ny,))
            ds_y.make_scale()
            ds_ix = h5main.create_dataset('ix', shape=(nx,))
            ds_ix.make_scale()
            ds_iy = h5main.create_dataset('iy', shape=(ny,))
            ds_iy.make_scale()
            ds_z = h5main.create_dataset('z', shape=(nz,))
            ds_z.make_scale()
            ds_t = h5main.create_dataset('time', shape=(nt,))
            ds_t.make_scale()
            for ds_name in dataset_names:
                ds = h5main.create_dataset(ds_name, shape=ds_shape,
                                           chunks=ds_chunk,
                                           compression=compression,
                                           compression_opts=compression_opts)
                for i, n in enumerate(plane_coord_order):
                    ds.dims[i].attach_scale(h5main[n])
                    if n == 'x':
                        ds.dims[i].attach_scale(h5main['ix'])
                    if n == 'y':
                        ds.dims[i].attach_scale(h5main['iy'])

            with h5py.File(hdf_filenames[0]) as h5plane:
                ds_x[:] = h5plane['x'][:]
                ds_y[:] = h5plane['y'][:]
                ds_ix[:] = h5plane['ix'][:]
                ds_iy[:] = h5plane['iy'][:]

                for ds_name in dataset_names:
                    for ak, av in h5plane[ds_name].attrs.items():
                        if not ak.isupper():
                            h5main[ds_name].attrs[ak] = av

                for n in ('x', 'y', 'ix', 'iy', 'z', 'time'):
                    for ak, av in h5plane[n].attrs.items():
                        if not ak.isupper():
                            h5main[n].attrs[ak] = av

            z_before_t = iz < it

            for iplane, plane_hdf_filename in enumerate(hdf_filenames):
                with h5py.File(plane_hdf_filename) as h5plane:
                    current_nt = h5plane['time'].size
                    if current_nt == nt:
                        ds_t[:] = h5plane['time'][:]
                    h5main['z'][iplane] = h5plane['z'][()]
                    for k in dataset_names:
                        ds = h5main[k]
                        if z_before_t:
                            ds[iplane, 0:current_nt] = h5plane[k][0:current_nt, ...]
                            if current_nt < nt:
                                ds[iplane, current_nt:] = np.nan
                        else:
                            for _it in range(current_nt):
                                ds[_it, iplane, ...] = h5plane[k][_it, :, :]
                            if current_nt < nt:
                                for _it in range(current_nt, nt):
                                    ds[_it, iplane, ...] = np.nan

        return target_hdf_filename

    @staticmethod
    def _merge_planes_unequal_time_vectors(hdf_filenames: List[pathlib.Path],
                                           target_hdf_filename: pathlib.Path):
        """merges multiple hdf files that have different time vectors lengths or entries"""
        nt_list = []
        x_data = []
        y_data = []
        z_data = []
        nz = len(hdf_filenames)
        dim_names = []
        for hdf_file in hdf_filenames:
            with h5py.File(hdf_file) as h5plane:
                nt_list.append(h5plane['time'].size)
                x_data.append(h5plane['x'][:])
                y_data.append(h5plane['y'][:])
                z_data.append(h5plane['z'][()])
                dim_names.append([d[0].name for d in h5plane['u'].dims])
        # different time steps --> put data in individual groups
        plane_grps = []
        with h5py.File(target_hdf_filename, 'w') as h5main:
            # h5main.attrs['software'] = PIVVIEW_SOFTWARE_NAME
            h5main.attrs['title'] = 'piv snapshot data'
            for iz, hdf_file in enumerate(hdf_filenames):
                plane_grp = h5main.create_group(f'plane{iz:0{len(str(nz))}}')
                plane_grps.append(plane_grp)
                with h5py.File(hdf_file) as h5plane:
                    for objname in h5plane:
                        if objname != PIV_PARAMETER_GRP_NAME:  # treat separately
                            h5main.copy(h5plane[objname], plane_grp)
            for varkey in ('x', 'y', 'ix', 'iy'):
                h5main.move(plane_grps[0][varkey].name, varkey)
                ds = h5main[varkey]
                for ak in ds.attrs.keys():
                    if ak.isupper():
                        del ds.attrs[ak]
                ds.make_scale()
                for plane_grp in plane_grps[1:]:
                    del plane_grp[varkey]

            for plane_grp in plane_grps[1:]:
                del plane_grp['z']
                for k, v in plane_grp.items():
                    if isinstance(v, h5py.Dataset):
                        for ak in ('DIMENSION_LIST',):
                            try:
                                del v.attrs[ak]
                            except KeyError:
                                pass
                        if v.ndim > 1:
                            for i, d in enumerate(dim_names[0]):
                                if 'time' in d and 'time' in plane_grp:
                                    v.dims[i].attach_scale(plane_grp['time'])
                                else:
                                    v.dims[i].attach_scale(h5main[d])
        return target_hdf_filename

    def to_hdf(self, hdf_filename: pathlib.Path = None, config: Dict = None,
               rtol=1.e-5, atol=1.e-8, fill_time_vec_differences: bool = False) -> pathlib.Path:
        """converts the snapshot into an HDF file"""
        if config is None:
            config = DEFAULT_CONFIGURATION
        else:
            if not isinstance(config, Dict):
                raise TypeError(f'Configuration must a dictionary, not {type(config)}')
        if hdf_filename is None:
            snapshot0_filename = self.list_of_piv_folder[0].list_of_piv_file[0].filename
            name = f'{snapshot0_filename.parent.parent}.hdf'
            hdf_filename = snapshot0_filename.parent.parent / name

        # get data from first snapshot to prepare the HDF5 file
        plane_hdf_files = [plane.to_hdf(generate_temporary_filename(suffix='_plane.hdf'), config) for plane
                           in self.list_of_piv_folder]
        hdf_filename = self.merge_planes(plane_hdf_files, hdf_filename, rtol, atol, fill_time_vec_differences)
        return hdf_filename
