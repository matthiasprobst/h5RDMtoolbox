import logging
import os
import pathlib
import time
from pathlib import Path
from typing import List, Dict, Union, Tuple

import h5py
import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial import qhull

from h5rdmtoolbox.utils import touch_tmp_hdf5_file
from .. import config

try:  # ipywdgets is not a must. bu if, then tqdm.notebook is quite nice to have...
    import ipywidgets
    from tqdm.notebook import tqdm
except ImportError:
    from tqdm import tqdm
from datetime import datetime
from . import core
from . import plane
from .snapshot import PIVSnapshotDatFile, PIVSnapshot
from ....conventions.translations import pivview_to_standardnames_dict, update_standard_names
from .. import vtk_utils
from ..calc import compute_z_derivative_of_z_velocity
from ..vtk_utils import result_3D_to_vtk
from ...._version import __version__

from .core import PIV_FILE_TYPE_NAME

logger = logging.getLogger('x2hdf')


class NCFilesCass:
    """Helper Class to provide information about the nc files to the user through the Plane class"""

    def __init__(self, files):
        self._files = files
        self._size = None

    def __len__(self):
        return len(self.files)

    def __repr__(self):
        return f'{len(self._files)} nc files -> total size: {self.size} Bytes ({round(self.size / 1000)} KB) '

    def __str__(self):
        return self.__repr__()

    @property
    def files(self) -> List:
        """returns all file paths"""
        return self._files

    @property
    def size(self) -> int:
        """returns the size of all nc files in bytes"""
        if self._size is None:
            self._size = np.sum([nc.stat().st_size for nc in self._files])
        return self._size


class PIVPlane(core.PIVNCConverter):
    snapshots: List[PIVSnapshot]
    performance = {'snapshot_read': [], 'snapshot_write': []}

    def __init__(self, plane_directory: pathlib.Path,
                 time_information: List[float] or float,
                 n: int = -1):
        """
        Parameters
        ----------
        plane_directory: pathlib.Path
            pathlib.Path to plane directory which contains netCDF4 (nc) files.
            An empty path ('') is interpreted as the cwd.
        time_information : List[float] or float
            List of time steps in seconds since start of recording (a time vector) or
            frequency in Hz. A frequency of 0 Hz will create a vector of zeros for all
            time steps.
        n : int, default=-1
            Number of snapshots to process. Default is n=-1 but setting it
            to 10 or so is useful for debug and testing (enhancing speed)
        """
        super().__init__(plane_directory)  # self.name is set in here

        # Catch empty root as "local"
        if plane_directory == '':
            self.name = pathlib.Path.cwd()
        self.name = self.name.absolute()

        found_nc_files = core.scan_for_timeseries_nc_files(self.name)
        logger.debug(f'Found files: {[f.name for f in found_nc_files]}')
        if n == -1:
            n = len(found_nc_files)
        if n == 0:
            raise ValueError('Number of found nc files is zero. Something went wrong. Please check '
                             f'the content of {self.name}')
        self._found_nc_files = found_nc_files

        if isinstance(time_information, (float, int)):  # a frequency is passed in [Hz]
            # build time vector
            if time_information == 0.:
                time_vector = np.zeros(n)
            else:
                time_vector = np.arange(0, n / time_information, 1 / time_information)
        else:
            time_vector = time_information

        self.recording_time = time_vector
        # ignore reading the parameters for each snapshot. it is enough to read once for a plane which
        # is already done a few lines above
        ignore_parameter_file = np.ones(len(time_vector)).astype(bool)
        ignore_parameter_file[0] = False
        self.snapshots = [PIVSnapshot(nc, recording_time=t, ignore_parameter_file=b) for (nc, t, b) in
                          zip(found_nc_files, time_vector, ignore_parameter_file)][:n]
        self.nt = len(self.snapshots)
        self.performance['snapshot_read'] = np.ones(self.nt).astype(np.float64)
        self.performance['snapshot_write'] = np.ones(self.nt).astype(np.float64)
        self.nz = 0

    def __len__(self):
        """returns number of snapshots"""
        return len(self.snapshots)

    @property
    def is_2d2c(self):
        return self.snapshots[0].is_2d2c

    def __str__(self):
        return f'PIV Plane Converter for plane {self.name} with {self.nt} nc files.'

    @core.piv_conversion
    def convert(self, target_hdf_filename: pathlib.Path = None,
                configuration: dict or pathlib.Path = None) -> pathlib.Path:
        """
        Converting method to convert input data into a single Case HDF file.

        Parameters
        ----------
        target_hdf_filename : pathlib.Path
            hdf file to fill with data from multiple planes --> case hdf file
        configuration: dict or pathlib.Path, optional=False
            Dictionary or path to yaml file. The configuration must provide the
            following keys:
                - interpolation
                - apply_mask
                - masking (if apply_mask==True)
                - z_source
            The default loads the user (default) configuration from the yaml file
            located at the tmp user data dir.

        Returns
        -------
        target_hdf_filename: pathlib.Path
            The file name of the plane hdf file
        """

        super().convert(target_hdf_filename, configuration=configuration)

        if not self.is_plane():
            raise core.PIVConversionInputError(self.name, self)

        if target_hdf_filename is None:
            target_hdf_filename = self.name.parent.joinpath(f'{self.name.stem}.hdf')
        self.hdf_filename = target_hdf_filename

        _, _, nc_variable_attr = self.snapshots[0].convert(create_hdf=True)  # will be deleted later on
        self.nx = self.snapshots[0].nx
        self.ny = self.snapshots[0].ny

        self._init_target_file(nc_variable_attr)

        self._convert_serial()

        st = time.perf_counter()
        if self.configuration['post']['running_mean']['compute']:
            # a convergence criterion is running mean of velocity
            self.compute_running_mean()
        logger.debug(f'computing running mean took: {time.perf_counter() - st} s')
        st = time.perf_counter()
        if self.configuration['post']['running_std']['compute']:
            # a convergence criterion is running std of velocity
            self.compute_running_std(ddof=2)
        logger.debug(f'computing running std took: {time.perf_counter() - st} s')

        pathlib.Path.unlink(self.snapshots[0].hdf_filename)

        return self.hdf_filename

    def _init_target_file(self, nc_variable_attr):
        """Creates empty datasets with correct structure (based on first snapshot).
        This is called during convert()"""
        with h5py.File(self.hdf_filename, 'w') as h5main:
            # reading from first snapshot HDF file which has been built already:
            with h5py.File(self.snapshots[0].hdf_filename, 'r') as h5snapshot:
                # copy root attributes from first snapshot to plane hdf target file:
                # this also includes pivview parameters because when converting the first
                # snapshot ignore_piv_parameters was set to False
                for ak, av in h5snapshot.attrs.items():
                    h5main.attrs[ak] = av

                h5main.create_dataset('x', data=h5snapshot['x'], maxshape=h5snapshot['x'].shape)
                h5main.create_dataset('y', data=h5snapshot['y'], maxshape=h5snapshot['y'].shape)
                h5main.create_dataset('ix', data=h5snapshot['ix'], maxshape=h5snapshot['ix'].shape)
                h5main.create_dataset('iy', data=h5snapshot['iy'], maxshape=h5snapshot['iy'].shape)
                h5main.create_dataset('z', data=h5snapshot['z'])
                ds_t = h5main.create_dataset('time', shape=len(self.snapshots))
                ds_t[0] = h5snapshot['time'][()]

                # make scale
                for cname in core.DIM_NAMES:
                    h5main[cname].make_scale(core.DEFAULT_DATASET_LONG_NAMES[cname])
                    if cname in nc_variable_attr:
                        core.copy_attributes(nc_variable_attr[cname], h5main[cname])

                # init datasets with full shape:
                for key in h5snapshot.keys():
                    if key not in core.DIM_NAMES:
                        _shape = (self.nt, self.ny, self.nx)
                        _chunks = (1, self.ny, self.nx)
                        ds = h5main.create_dataset(key,
                                                   shape=_shape,
                                                   maxshape=_shape,
                                                   chunks=_chunks,
                                                   compression=self.configuration['compression'],
                                                   compression_opts=self.configuration['compression_opts'])

                        # copy variable attributes (only done once!)
                        logger.debug(f'Copying attributes for dataset {key}')
                        if key in h5snapshot.keys():
                            core.copy_attributes(h5snapshot[key].attrs, ds)

                        ds.dims[0].attach_scale(h5main['time'])
                        ds.dims[1].attach_scale(h5main['y'])
                        ds.dims[2].attach_scale(h5main['x'])
                        ds.dims[1].attach_scale(h5main['iy'])
                        ds.dims[2].attach_scale(h5main['ix'])
                        ds.attrs['COORDINATES'] = ['z', ]

    def _convert_serial(self):
        with h5py.File(self.hdf_filename, 'r+') as h5main:

            # datasets are already initialized and 'x', 'y', 'z' and 'time' are filled with data
            # snapshot.convert gets parameter create_hdf=False and will not create and HDF5 file
            # it also will not (!) compute x,y,z unless interpolation is set to True in which case
            # the coordinates are needed. For interpolation=False this implementation should give
            # some speed-up

            # loop over all snapshots and convert them without writing a snapshot-HDF5 file
            for i_snapshot, snapshot in tqdm(enumerate(self.snapshots), unit=' snapshots', total=self.nt):
                st = time.perf_counter()
                nc_data, _, nc_variable_attr = snapshot.convert(create_hdf=False)  # no creation of x,y,z
                self.performance['snapshot_read'][i_snapshot] = time.perf_counter() - st
                st = time.perf_counter()
                _ = self.write_snapshot_nc_data_to_hdf(nc_data=nc_data, h5grp=h5main, iz=None, it=i_snapshot)
                self.performance['snapshot_write'][i_snapshot] = time.perf_counter() - st

            if self.configuration['timeAverages']['compute']:
                if self.configuration['timeAverages']['use_nc']:
                    NotImplementedError()
                else:
                    # calculate timeAverages:
                    av_grp = h5main.create_group('timeAverages')
                    av_grp.attrs['long_name'] = 'Time averaged datasets.'
                    for key in h5main.keys():
                        if key not in core.DIM_NAMES:
                            if key not in ('valid', 'piv_flags') and isinstance(h5main[key], h5py.Dataset):
                                _shape = (self.ny, self.nx)
                                _chunks = (self.ny, self.nx)

                                av_ds = av_grp.create_dataset(name=key, shape=_shape, maxshape=_shape, chunks=_chunks,
                                                              compression=self.configuration['compression'],
                                                              compression_opts=self.configuration['compression_opts'])
                                av_ds[:] = np.mean(h5main[key][...], axis=0)

                                # attach_scale
                                for ic, c in enumerate((('y', 'iy'), ('x', 'ix'))):
                                    av_ds.dims[ic].attach_scale(h5main[c[0]])
                                    av_ds.dims[ic].attach_scale(h5main[c[1]])

                                # copy attributes from first nc file
                                av_ds.attrs[self.configuration['attrs_unit_name']] = h5main[key].attrs[
                                    self.configuration['attrs_unit_name']
                                ]
                                if 'long_name' in h5main[key].attrs:
                                    av_ds.attrs['long_name'] = h5main[key].attrs['long_name']
                                if 'standard_name' in h5main[key].attrs:
                                    av_ds.attrs['standard_name'] = h5main[key].attrs['standard_name']

    def _convert_parallel(self, nproc):
        raise NotImplementedError()

    def compute_running_std(self, ddof: int = 2):
        """Computing running std for convergence judgment"""
        with h5py.File(self.hdf_filename, 'r+') as h5main:
            core.compute_running_std(h5main, self.configuration, ddof)

    def compute_running_mean(self):
        """Computing running mean for convergence judgment"""
        with h5py.File(self.hdf_filename, 'r+') as h5main:
            core.compute_running_mean(h5main, self.configuration)

    def to_vtk(self, vtk_filename_wo_suffix: str = None, it=None):
        """Converts a snapshot or the time-averaged data into a vtk file.

        Parameters
        ----------
        vtk_filename_wo_suffix : pathlib.Path
            File name without suffix to write vtk data to.
        it : int, optional=None
            Timestep to export. If None, time averaged data is taken.

        Returns
        -------
        None
        """
        super().to_vtk(vtk_filename_wo_suffix=vtk_filename_wo_suffix)

        data = dict()
        with h5py.File(self.hdf_filename, 'r') as h5:
            if it is None and 'timeAverages' not in h5:
                raise ValueError(f'No time-averaged ("timeAverages") data available in {self.hdf_filename}.')
            x = h5['x'][()]
            y = h5['y'][()]
            z = h5['z'][()]
            xx, yy, zz = np.meshgrid(x, y, z, indexing='ij')
            data['x'] = xx  # vtk only accepts 3d data
            data['y'] = yy
            data['z'] = zz
            if it is None:
                ta = h5['timeAverages']
                for k in ta.keys():
                    ds = ta[k]

                    if ds.ndim == 4:
                        for i in range(ds.shape[-1]):
                            data[f'{ds.name}-{i}'] = ds[..., i].T
                    else:
                        data[k] = ds[...].T
            else:
                for k, ds in h5.keys():
                    if k not in core.DIM_NAMES:
                        if isinstance(ds, h5py.Dataset):
                            if ds.ndim == 5:
                                for i in range(ds.shape[-1]):
                                    data[f'{ds.name}-{i}'] = ds[:, it, ..., i].T
                            else:
                                data[k] = ds[:, it, ...].T

        _, vtk_path = result_3D_to_vtk(data, target_filename=str(self.vtk_file_name))

    def write_snapshot_nc_data_to_hdf(self, nc_data: Dict, h5grp: h5py.Group, iz: Union[int, None], it: int):
        """
        Write snapshot nc data to the respective datasets in the HDF file. The datasets
        must already exist and have the correct size and shape in order to write to
        the requested array location (iz, it).

        Parameters
        ----------
        h5grp : h5py.Group
            HDF5 group of an opened hdf file instance to write data to.
        iz : int or None
            Plane index. If None, datasets are expected not to have a z-axis!
        it : int
            Time index

        Returns
        -------
        h5grp : h5py.Group
            The HDF5 group in wich data was written.

        """
        if iz is None:
            for nc_key in nc_data.keys():
                try:
                    if nc_key == 'time':
                        h5grp['time'][it] = nc_data[nc_key]
                    else:
                        h5grp[nc_key][it, ...] = nc_data[nc_key][:]
                except KeyError as e:
                    raise ValueError(f'Following key was not found in {self.name}: {e}')
        else:
            for nc_key in nc_data.keys():
                try:
                    if nc_key == 'time':
                        h5grp['time'][it] = nc_data[nc_key]
                    else:
                        h5grp[nc_key][iz, it, ...] = nc_data[nc_key][:]
                except KeyError as e:
                    raise ValueError(f'Following key was not found in {self.name}: {e}')

        return h5grp

    @property
    def nc(self) -> NCFilesCass:
        """returns object of NCFilesCass to provide information about ncetCDF4 files used for the plane"""
        return NCFilesCass(self._found_nc_files)


class MultiPlaneInputError(Exception):
    """Error is raised if input for PIVCase is wrong"""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def _generate_plane_group(iz, nz):
    return f'plane{iz:0{len(str(nz))}}'


def merge_multiple_plane_hdf_files(plane_hdf_files: List[pathlib.Path], target_filename: pathlib.Path = None,
                                   take_min_nt: bool = True, remove_plane_hdf_files: bool = True,
                                   configuration: Union[dict, None] = None) -> pathlib.Path:
    """merges multiple plane hdf files to a single case hdf file and returns the case hdf file

    Parameters
    ----------
    plane_hdf_files : List[pathlib.Path]
        List of plane HDF filenames
    target_filename : pathlib.Path
        HDF5 filename to write merged data to
    take_min_nt : bool
        If planes have unequal number of time steps either min or max number of timesteps are
        realized in the target case file. Default is to take the minimum. If maximum is taken
        non-existing data is filled up with NaNs.
    remove_plane_hdf_files : bool
        Whether to remove plane hdf files. Default is True

    Returns
    -------
    target_filename : pathlib.Path
        The created PIVview case HDF5 file
    """
    if target_filename is None:
        save_path = pathlib.Path(*os.path.commonprefix([p.resolve().parts for p in plane_hdf_files]))
        target_filename = pathlib.Path.joinpath(save_path.parent, f'{save_path.name}.hdf')
        logger.debug(f'saving to {save_path}')
    shape_list = []
    for plane_hdf in plane_hdf_files:
        with h5py.File(plane_hdf, 'r') as h5:
            shape_list.append(h5['u'].shape)
    if not all([len(s) == 3 for s in shape_list]):
        raise ValueError('All plane HDF files must contain 3D PIV data arrays!')

    if take_min_nt:
        nt = min([s[0] for s in shape_list])  # min nt over planes
    else:
        nt = max([s[0] for s in shape_list])

    nz = len(plane_hdf_files)

    with h5py.File(target_filename, 'w') as h5case:

        now = datetime.now()

        h5case.attrs['__h5rdmtoolbox_version__'] = __version__
        if configuration is None:
            configuration = config
        h5case.attrs['creation_time'] = now.strftime(configuration['datetime_str'])
        h5case.attrs['piv_data_type'] = PIV_FILE_TYPE_NAME['PIVMultiPlane']
        h5case.attrs['title'] = core.MULTIPLANE_TITLE

        grp_av = h5case.create_group('timeAverages')
        # create a plane grp for every plane:
        h5planegroups = []
        for iz in range(nz):
            h5planegroups.append(h5case.create_group(_generate_plane_group(iz, nz)))

        time_vectors = []
        for plane_hdf_file in plane_hdf_files:
            with h5py.File(plane_hdf_file, 'r') as h5plane:
                time_vectors.append(h5plane['time'][:])

        for it, tv in enumerate(time_vectors):
            if len(tv) < nt:
                time_vectors[it] = np.zeros(shape=(nt,)).astype(tv.dtype)
                time_vectors[it][0:len(tv)] = tv
                time_vectors[it][len(tv):] = np.nan

        if np.all([nt == len(tv) for tv in time_vectors]):
            one_freq_for_all_planes = np.all([time_vectors[0][0:nt] == tv[0:nt] for tv in time_vectors])
        else:
            one_freq_for_all_planes = False

        # open first plane in read mode and initialize all datasets and write already some data
        with h5py.File(plane_hdf_files[0], 'r') as h5plane:
            if 'piv_dimension' in h5plane.attrs:
                h5case.attrs['piv_dimension'] = h5plane.attrs['piv_dimension']
            core.copy_attributes(h5plane['timeAverages'].attrs, grp_av)

            # copy piv parameters from first plane to attribute plane0 of group PIV_PARAMETER_HDF_NAME
            iz = 0
            h5planegroups[iz].attrs[core.PIV_PARAMTER_HDF_NAME] = h5plane.attrs[core.PIV_PARAMTER_HDF_NAME]
            nx = h5plane['x'].size
            ny = h5plane['y'].size

            h5plane_keys = [k for k in h5plane.keys() if k not in core.DIM_NAMES]

        if one_freq_for_all_planes:

            with h5py.File(plane_hdf_files[0], 'r') as h5plane:
                # create coordinates at root level:
                for k in ('time', 'x', 'y', 'ix', 'iy'):
                    _ds = h5case.create_dataset(k, data=h5plane[k],
                                                compression=h5plane[k].compression,
                                                compression_opts=h5plane[k].compression_opts)
                    core.copy_attributes(h5plane[k].attrs, _ds)

                ds_z = h5case.create_dataset('z', shape=(nz,),
                                             compression=h5plane['x'].compression,
                                             compression_opts=h5plane['x'].compression_opts)
                ds_z[iz] = h5plane['z'][()]
                core.copy_attributes(h5plane['z'].attrs, ds_z)

                for ds in h5plane_keys:
                    if isinstance(h5plane[ds], h5py.Dataset):
                        _ds = h5case.create_dataset(ds, shape=(nz, nt, ny, nx),
                                                    compression=h5plane[ds].compression,
                                                    compression_opts=h5plane[ds].compression_opts)
                        nt_source = h5plane[ds].shape[0]
                        _ds[0, 0:nt_source, ...] = h5plane[ds][:nt_source, ...]
                        if nt - nt_source > 0:
                            _ds[0, nt_source:, ...] = np.nan
                        core.copy_attributes(h5plane[ds].attrs, _ds)
                        # attach scales:
                        _ds.dims[0].attach_scale(h5case['z'])
                        _ds.dims[1].attach_scale(h5case['time'])
                        _ds.dims[2].attach_scale(h5case['y'])
                        _ds.dims[3].attach_scale(h5case['x'])

                # now, go through all the other plane files:
                for iplane, plane_hdf in enumerate(plane_hdf_files[1:]):
                    iz = iplane + 1

                    # write pivview parameters to group
                    with h5py.File(plane_hdf, 'r') as h5plane:
                        h5planegroups[iz].attrs[core.PIV_PARAMTER_HDF_NAME] = h5plane.attrs[core.PIV_PARAMTER_HDF_NAME]

                        h5case['z'][iz] = h5plane['z'][()]

                        for ds_name in h5plane_keys:
                            if isinstance(h5plane[ds_name], h5py.Dataset):
                                nt_source = h5plane[ds_name].shape[1]
                                if one_freq_for_all_planes:
                                    h5case[ds_name][iz, 0:nt_source, ...] = h5plane[ds_name][0:nt_source, ...]
                                    if nt - nt_source > 0:
                                        h5case[ds_name][iz, nt_source:, ...] = np.NAN
        else:

            for iz, plane_hdf in enumerate(plane_hdf_files):
                with h5py.File(plane_hdf, 'r') as h5plane:
                    planegrp = h5planegroups[iz]
                    # create coordinates at plane group level:
                    for k in ('time', 'x', 'y', 'ix', 'iy'):
                        _ds = planegrp.create_dataset(k, data=h5plane[k],
                                                      compression=h5plane[k].compression,
                                                      compression_opts=h5plane[k].compression_opts)
                        core.copy_attributes(h5plane[k].attrs, _ds)
                        _ds.make_scale()

                    ds_z = planegrp.create_dataset('z', data=h5plane['z'][()])
                    core.copy_attributes(h5plane['z'].attrs, ds_z)

                    for ds in h5plane_keys:
                        if isinstance(h5plane[ds], h5py.Dataset):
                            _ds = planegrp.create_dataset(ds, shape=h5plane[ds].shape,
                                                          data=h5plane[ds][:],
                                                          compression=h5plane[ds].compression,
                                                          compression_opts=h5plane[ds].compression_opts)
                            core.copy_attributes(h5plane[ds].attrs, _ds)
                            # attach scales to dataset:
                            _ds.attrs['COORDINATES'] = 'z'
                            _ds.dims[0].attach_scale(planegrp['time'])
                            _ds.dims[1].attach_scale(planegrp['y'])
                            _ds.dims[2].attach_scale(planegrp['x'])
                            _ds.dims[1].attach_scale(planegrp['iy'])
                            _ds.dims[2].attach_scale(planegrp['ix'])

    if remove_plane_hdf_files:
        logger.debug(f'Deleting plane hdf files {plane_hdf_files}')
        for plane_hdf_file in plane_hdf_files:
            plane_hdf_file.unlink()

    return target_filename


class PIVMultiPlane(core.PIVNCConverter):
    planes: List[PIVPlane]
    input_is_hdf: bool = False  # that's the the default; other is "hdffiles"
    one_freq_for_all_planes: bool = False  # just a flag to check whether the user put in a recording frequency or

    # individual time stamps

    def __init__(self, plane_folder_list: Union[List, Tuple],
                 time_information: [List, Tuple],
                 n: int = -1):
        """
        Conversion class to build a single HDF file out of multiple plane PIV recordings.

        Parameters
        ----------
        plane_folder_list : List[pathlib.Path]
            List of paths to plane directory or list of paths of already (with this package) converted plane *.hdf
            files, that should be collected in one case. Obviously, the dimensions of the single plane data hast to
            be same in x and y (t will be taken care of).
            Important: Make sure list is sorted by ascending z-coordinate!!! This is not checked!!!
        time_information : float or List
            Frequency to take for all planes or List of frequencies to take for all planes
            or List of array-like data with each entry being the exact time vector for the respective plane.
        n : int, optional = -1
            number of snapshots to process per plane.
            Default is -1 which takes all
        """
        plane_folder_list = [pathlib.Path(p) for p in plane_folder_list]  # lazy user may not have passed pathlib type
        all_dirs = all([p.is_dir() for p in plane_folder_list])
        all_files = all([p.is_file() for p in plane_folder_list])
        if not all_dirs and not all_files:
            raise MultiPlaneInputError('Input must be list of plane directories or list of plane HDF files!')

        #  Check whether frequency or timestamps were passed
        if isinstance(time_information, (float, int)):
            # Assuming, that frequency is passed in time_information
            self.one_freq_for_all_planes = True  # one time vector for all planes!
            plane_time_information = [time_information, ] * len(plane_folder_list)
        else:
            # Assuming that either list of frequencies or list of lists where each contains timestamps of snapshots
            # individual frequencies per plane or individual time vectors per plane, thus build a dataset called
            # "snapshot_index" and "time". the "snapshot_index" is used to attach the dimension, not "time"
            plane_time_information = time_information
            if np.all([t == time_information[0] for t in time_information[1:]]):
                self.one_freq_for_all_planes = True

        self.input_is_hdf = all_files
        if self.input_is_hdf:  # if not, use the default, which is "directories" (see class level attribute definition)
            # check if a list of HDF files was passed and not some other file format...
            nt = []
            for p in plane_folder_list:
                try:
                    with h5py.File(p, 'r') as h5:
                        if 'time' in h5:
                            nt.append(h5['time'].size)
                        else:
                            raise KeyError('No dataset "time" found in plane hdf file. Check if input '
                                           'is a valid PIVview plane-hdf file!')
                except OSError as e:
                    raise MultiPlaneInputError(f'Only HDF5 files are accepted as input files.\n'
                                               f'Could not read input file due to: {e}')

            if len(plane_folder_list) == 1:
                save_path = plane_folder_list[0].resolve().parent
            else:
                save_path = pathlib.Path(*os.path.commonprefix([p.resolve().parts for p in plane_folder_list]))

            self.planes = [hdf_filename for hdf_filename in plane_folder_list]

            # determine nz and nt:
            self.nt = min(nt)
            self.nz = len(plane_folder_list)
        else:
            # Check which folders can - at all - be a potential PIVPlane (--> must contain *.nc files...)
            verified_folders = [fp for fp in plane_folder_list if core.folder_has_nc_files(fp)]
            nplanes = len(verified_folders)
            if not nplanes == len(plane_folder_list):
                raise ValueError('Not all passed folders contain nc files! Please check and retry.')
            # self.nz = nplanes

            # Choose the closest common directory of all verified plane folder paths. This will be the name of
            # the case
            # if only one folder was passed this would lead to the lane folder and not to the case folder:
            if len(verified_folders) == 1:
                save_path = verified_folders[0].parent
            else:
                save_path = pathlib.Path(*os.path.commonprefix([vf.resolve().parts for vf in verified_folders]))

            self.planes = [PIVPlane(fp, t, n=n) for (fp, t) in zip(verified_folders, plane_time_information)]

            # determine nz and nt:
            self.nt = min([p.nt for p in self.planes])  # min nt over planes
            self.nz = len(self.planes)

        super().__init__(name=save_path.absolute())  # Sets self.name=name (in parent-parent-class __init__())

    def __len__(self):
        """returns number of planes"""
        return len(self.planes)

    @property
    def is_2d2c(self):
        """returns the 'is_2d2c' state of the very first snapshot"""
        if isinstance(self.planes[0], pathlib.Path):
            if self.planes[0].hdf_filename.exists():
                with h5py.File(self.planes[0], 'r') as h5:
                    return h5.attrs['piv_dimension'] == '2D2C'
            return None
        return self.planes[0].snapshots[0].is_2d2c

    @core.piv_conversion
    def convert(self, target_hdf_filename: pathlib.Path = None,
                configuration: Union[Dict, pathlib.Path, None] = None) -> pathlib.Path:
        """
        Converting method to convert input data into a single Case HDF file.

        Parameters
        ----------
        target_hdf_filename : pathlib.Path
            hdf file to fill with data from multiple planes --> case hdf file
        configuration: dict or pathlib.Path, optional=False
            Dictionary or path to yaml file. The configuration must provide the
            following keys:
                - interpolation
                - apply_mask
                - masking (if apply_mask==True)
                - z_source
            The default loads the user (default) configuration from the yaml file
            located at the tmp user data dir.

        Returns
        -------
        target_hdf_filename: pathlib.Path
            The file name of the case hdf file
        """
        super().convert(target_hdf_filename, configuration=configuration)

        if target_hdf_filename is None:
            target_hdf_filename = pathlib.Path.joinpath(self.name.parent, f'{self.name.stem}.hdf').resolve()
        self.hdf_filename = target_hdf_filename

        if self.input_is_hdf:
            if 'take_min_nt' not in self.configuration:
                raise KeyError('Your yaml configuration file seems not to be up-to-date. At least config entry '
                               '"take_min_nt" is missing')
            _ = merge_multiple_plane_hdf_files(self.planes, self.hdf_filename, self.configuration['take_min_nt'])
        else:
            if self.one_freq_for_all_planes:
                self._init_target_file()
                # Actual Conversion !
                # self._convert_serial_individual_plane()
            else:
                self._init_target_file_with_individual_plane_groups()
            # Actual Conversion !
            self._convert_serial()
            # _init_target_file() has created a HDF file for each first snapshot of a plane.
            # The others a kept in RAM. Those files must be deleted:
            for _plane in self.planes:
                pathlib.Path.unlink(_plane.snapshots[0].hdf_filename)

        st = time.perf_counter()
        if self.configuration['post']['running_mean']['compute']:
            # a convergence criterion is running mean of velocity
            self.compute_running_mean()
        logger.debug(f'computing running mean took: {time.perf_counter() - st} s')
        st = time.perf_counter()
        if self.configuration['post']['running_std']['compute']:
            # a convergence criterion is running std of velocity
            self.compute_running_std(ddof=2)
        logger.debug(f'computing running std took: {time.perf_counter() - st} s')

        return target_hdf_filename

    def _generate_plane_group(self, iz: int):
        # leading zero only if nz > 9 or 99 ...
        return _generate_plane_group(iz, self.nz)

    def _init_target_file_with_individual_plane_groups(self):
        for _plane in self.planes:
            _plane.snapshots[0].convert(None, create_hdf=True)
        self.nx = self.planes[0].snapshots[0].nx
        self.ny = self.planes[0].snapshots[0].ny

        with h5py.File(self.hdf_filename, 'w') as h5main:

            for iz in range(self.nz):
                gr = h5main.create_group(self._generate_plane_group(iz))
                gr.attrs['directory'] = str(self.planes[iz].name.resolve())

                with h5py.File(self.planes[iz].snapshots[0].hdf_filename, 'r') as h5snapshot:

                    # we have not yet written x, y, z, ix, iy and time to each plane group:
                    for k in ('x', 'y', 'ix', 'iy'):
                        ds = gr.create_dataset(k, data=h5snapshot[k])
                        ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[k])
                        ds.attrs['standard_name'] = h5snapshot[k].attrs['standard_name']
                        ds.attrs['units'] = h5snapshot[k].attrs['units']

                    # create an individual time axis for every plane because
                    # recording time is individual!
                    dsz = gr.create_dataset('z', data=h5snapshot['z'][()])
                    dsz.attrs['standard_name'] = h5snapshot['z'].attrs['standard_name']
                    dsz.attrs['units'] = h5snapshot['z'].attrs['units']

                    dst = gr.create_dataset('time', shape=(self.nt,))
                    dst.attrs['standard_name'] = h5snapshot['time'].attrs['standard_name']
                    dst.attrs['units'] = h5snapshot['time'].attrs['units']

                    # first snapshot of first plane can be written already:
                    dst[0] = h5snapshot['time'][()]

                    # dataset for each plane individually:
                    for k, v in h5snapshot.items():
                        if k not in core.DIM_NAMES:
                            _shape = (self.nt, self.ny, self.nx)
                            _chunks = (1, self.ny, self.nx)
                            ds = gr.create_dataset(
                                name=k,
                                shape=_shape,
                                maxshape=_shape,
                                chunks=_chunks,
                                compression=self.configuration['compression'],
                                compression_opts=self.configuration[
                                    'compression_opts'])

                            ds[0, ...] = h5snapshot[k][...]
                            ds.dims[0].attach_scale(dst)
                            ds.dims[1].attach_scale(gr['y'])
                            ds.dims[2].attach_scale(gr['x'])
                            ds.dims[1].attach_scale(gr['iy'])
                            ds.dims[2].attach_scale(gr['ix'])
                            ds.attrs.modify('COORDINATES', ['z', ])

                            for ak, av in h5snapshot[k].attrs.items():
                                if ak not in ('DIMENSION_LIST', 'CLASS', 'NAME', 'REFERENCE_LIST', 'COORDINATES'):
                                    ds.attrs.modify(ak, av)

    def _init_target_file(self):
        """Creates empty datasets with correct structure (based on first snapshot).
        This is called during convert()"""

        # Convert the very first snapshot of all planes. This will give all needed information about file content
        # The creation of HDF files for each first snapshot is needed to get the PIVview Parameters/Configuration
        # Those files will be deleted later on
        for _plane in self.planes:
            _plane.snapshots[0].convert(target_hdf_filename=None, create_hdf=True)
        self.nx = self.planes[0].snapshots[0].nx
        self.ny = self.planes[0].snapshots[0].ny

        with h5py.File(self.hdf_filename, 'w') as h5main:

            # create a group for each plane to provide plane information there
            for iz in range(self.nz):
                gr = h5main.create_group(f'plane{iz:0{len(str(self.nz))}}')  # leading zero only if nz > 9 or 99 ...
                gr.attrs['directory'] = str(self.planes[iz].name.resolve())

            # read first snapshot and prepare main/target hdf file
            with h5py.File(self.planes[0].snapshots[0].hdf_filename, 'r') as h5snapshot:
                for ak, av in h5snapshot.attrs.items():
                    if ak not in (*core.IGNORE_ATTRS, core.PIV_PARAMTER_HDF_NAME, 'plane_directory'):
                        h5main.attrs[ak] = av

                # x, y, z and time can be stored at root group:
                # write x, y to root group:
                for k in ('x', 'y', 'ix', 'iy'):
                    ds = h5main.create_dataset(k, data=h5snapshot[k])
                    ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[k])
                    ds.attrs['standard_name'] = h5snapshot[k].attrs['standard_name']
                    ds.attrs['units'] = h5snapshot[k].attrs['units']

                # create an individual time axis for every plane because
                # recording time is individual!
                dsz = h5main.create_dataset('z', shape=(self.nz,))
                dsz[0] = h5snapshot['z'][()]
                dsz.attrs['standard_name'] = h5snapshot['z'].attrs['standard_name']
                dsz.attrs['units'] = h5snapshot['z'].attrs['units']

                dst = h5main.create_dataset('time', shape=(self.nt,))
                dst.attrs['standard_name'] = h5snapshot['time'].attrs['standard_name']
                dst.attrs['units'] = h5snapshot['time'].attrs['units']
                dst[0] = h5snapshot['time'][()]

                # init the dataset shapes for all datasets. time axis included as time is equal for all planes
                for k, v in h5snapshot.items():
                    if k not in core.DIM_NAMES:
                        _shape = (self.nz, self.nt, self.ny, self.nx)
                        _chunks = (1, 1, self.ny, self.nx)
                        ds = h5main.create_dataset(name=k,
                                                   shape=_shape,
                                                   maxshape=_shape,
                                                   chunks=_chunks,
                                                   compression=self.configuration['compression'],
                                                   compression_opts=self.configuration['compression_opts'])
                        for ak, av in h5snapshot[k].attrs.items():
                            if ak not in ('DIMENSION_LIST', 'CLASS', 'NAME', 'REFERENCE_LIST', 'COORDINATES'):
                                ds.attrs[ak] = av

            # open first snapshot of all planes (which are already converted)
            # and write x,y,z data:
            for iplane, _plane in enumerate(self.planes):
                with h5py.File(_plane.snapshots[0].hdf_filename, 'r') as h5snapshot:
                    for dsname, ds in h5snapshot.items():
                        if dsname not in core.DIM_NAMES:
                            h5main[dsname][iplane, 0, ...] = ds[:]
                    h5main['z'][iplane] = h5snapshot['z'][()]

    def _convert_serial_individual_plane(self):
        """as time vector is different for all plane recordings, plane data is in separate groups"""
        pass

    def _convert_serial(self):
        """Serial conversion for planes with equal time vector. Runs over all snapshots of all planes and reads data
        into RAM. Then writes it to case hdf file which is opened during all that looping."""
        vel_abs_name = self.configuration['post']['velocity_abs_ds_name']
        with h5py.File(self.hdf_filename, 'r+') as h5main:
            for iplane, _plane in enumerate(self.planes):
                if self.one_freq_for_all_planes:
                    target_group = h5main
                    iz = iplane
                else:
                    iz = None
                    target_group = h5main[f'plane{iplane:0{len(str(self.nz))}}']
                for it, snapshot in tqdm(enumerate(_plane.snapshots[1:self.nt]), unit=' snapshots',
                                         total=self.nt - 1):
                    nc_data, _, nc_variable_attr = snapshot.convert(
                        create_hdf=False)  # snapshot data is not written to file but kept in RAM
                    _plane.configuration = self.configuration  # plane instance has not yet the configuration
                    _plane.write_snapshot_nc_data_to_hdf(nc_data, target_group, iz, it + 1)
                    if it == 0:
                        for key in nc_variable_attr.keys():
                            if key in target_group:
                                core.copy_attributes(nc_variable_attr[key], target_group[key])

            self.compute_magnitude_of_velocitys()

            # calculate timeAverages:
            if self.configuration['timeAverages']['compute']:
                av_grp = h5main.create_group('timeAverages')
                av_grp.attrs['long_name'] = 'Time averaged datasets.'

                if self.one_freq_for_all_planes:
                    for key in h5main.keys():
                        if key not in core.DIM_NAMES:
                            # if isinstance(h5main[key], h5py.Dataset): # at this point there are no groups yet
                            if key not in ('valid', 'piv_flags', vel_abs_name) and isinstance(
                                    h5main[key], h5py.Dataset):
                                _shape = (self.nz, *h5main[key].shape[2:])
                                if h5main[key].ndim == 4:
                                    _chunks = (self.nz, *_shape[1:])
                                else:
                                    _chunks = (self.nz, *_shape[1:-1], 1)
                                av_ds = av_grp.create_dataset(name=key, shape=_shape, maxshape=_shape, chunks=_chunks,
                                                              compression=self.configuration['compression'],
                                                              compression_opts=self.configuration['compression_opts'])
                                av_ds[...] = np.mean(h5main[key][...], axis=1)
                                # attach_scale
                                av_ds.dims[0].attach_scale(h5main['z'])
                                for ic, c in zip((1, 2), (('y', 'iy'), ('x', 'ix'))):
                                    av_ds.dims[ic].attach_scale(h5main[c[0]])
                                    av_ds.dims[ic].attach_scale(h5main[c[1]])

                                # copy attributes from root datasets to time averaged:
                                core.copy_attributes(h5main[key].attrs, av_ds)
                else:
                    # compute time Averages for plane data
                    err = False
                    for k in h5main.keys():
                        if 'plane' in k and k != 'plane0':
                            if not np.array_equal(h5main['plane0']['x'][:], h5main[k]['x'][:]):
                                logger.error('Cannot compute time averages because coordinates of '
                                             'planes are not identical')
                            if not np.array_equal(h5main['plane0']['y'][:], h5main[k]['y'][:]):
                                logger.error('Cannot compute time averages because coordinates of '
                                             'planes are not identical')
                            err = True
                    if not err:
                        iz = 0
                        grp0name = f'plane{iz:0{len(str(self.nz))}}'
                        dset_x = h5main['timeAverages'].create_dataset('x', data=h5main[grp0name]['x'])
                        dset_x.attrs['standard_name'] = 'x_coordinate'
                        dset_x.attrs['units'] = h5main[grp0name]['x'].attrs['units']
                        dset_y = h5main['timeAverages'].create_dataset('y', data=h5main[grp0name]['y'])
                        dset_y.attrs['standard_name'] = 'y_coordinate'
                        dset_y.attrs['units'] = h5main[grp0name]['y'].attrs['units']
                        dset_z = h5main['timeAverages'].create_dataset('z', shape=(self.nz,))
                        dset_z.attrs['standard_name'] = 'z_coordinate'
                        dset_z.attrs['units'] = h5main[grp0name]['z'].attrs['units']

                        for iplane, planegrp in enumerate(
                                [h5main[f'plane{iz:0{len(str(self.nz))}}'] for iz in range(self.nz)]):
                            dset_z[iplane] = planegrp['z'][()]
                            for key in planegrp.keys():
                                if key not in ('valid', 'piv_flags', 'time', 'x', 'y', 'z') and isinstance(
                                        planegrp[key],
                                        h5py.Dataset):
                                    if iplane == 0:
                                        _shape = (self.nz, *planegrp[key].shape[1:])
                                        _chunks = (1, *planegrp[key].shape[1:])

                                        av_ds = av_grp.create_dataset(name=key, shape=_shape, maxshape=_shape,
                                                                      chunks=_chunks,
                                                                      compression=self.configuration['compression'],
                                                                      compression_opts=self.configuration[
                                                                          'compression_opts'])
                                        # attach_scale
                                        av_ds.dims[0].attach_scale(h5main['timeAverages']['z'])
                                        for ic, c in zip((1, 2), (('y', 'iy'), ('x', 'ix'))):
                                            av_ds.dims[ic].attach_scale(h5main['timeAverages'][c[0]])
                                            av_ds.dims[ic].attach_scale(h5main['timeAverages'][c[1]])

                                        # copy attributes from root datasets to time averaged:
                                        core.copy_attributes(planegrp[key].attrs, av_ds)

                                    else:
                                        av_ds = av_grp[key]
                                    av_ds[iplane, ...] = np.mean(planegrp[key][...], axis=0)

                # at the end, write PIVview parameters/configuration of all planes in separate group

                # piv_par_grp = h5main.create_group(
                #     core.PIV_PARAMTER_HDF_NAME)  # group to store parameters or configuration.
                # piv_par_grp.attrs['long_name'] = 'Group providing PIV evaluation settings for each plane'
                for iz, _plane in enumerate(self.planes):
                    grpname = f'plane{iz:0{len(str(self.nz))}}'
                    # the first snapshot file is created every other not
                    with h5py.File(_plane.snapshots[0].hdf_filename, 'r') as h5plane:
                        h5main[grpname].attrs[core.PIV_PARAMTER_HDF_NAME] = h5plane.attrs[core.PIV_PARAMTER_HDF_NAME]

    def _convert_parallel(self):
        """Parallel conversion. Not implemented yet."""
        raise NotImplementedError(f'Parallel Processing for case not implemented yet')

    def compute_running_std(self, ddof: int = 2):
        """Computing running std for convergence judgment"""
        if self.one_freq_for_all_planes:
            with h5py.File(self.hdf_filename, 'r+') as h5main:
                core.compute_running_std(h5main, self.configuration, ddof)
        else:
            with h5py.File(self.hdf_filename, 'r+') as h5main:
                for plane_grp in [h5main[f'plane{iz:0{len(str(self.nz))}}'] for iz in range(self.nz)]:
                    core.compute_running_std(plane_grp, self.configuration, ddof)

    def compute_running_mean(self):
        """Computing running mean for convergence judgment"""
        if self.one_freq_for_all_planes:
            with h5py.File(self.hdf_filename, 'r+') as h5main:
                core.compute_running_mean(h5main, self.configuration)
        else:
            with h5py.File(self.hdf_filename, 'r+') as h5main:
                for plane_grp in [h5main[f'plane{iz:0{len(str(self.nz))}}'] for iz in range(self.nz)]:
                    core.compute_running_mean(plane_grp, self.configuration)

    def compute_intermediate_plane(self, z: np.ndarray or int,
                                   only_time_averages: bool = True,
                                   method='linear') -> pathlib.Path:
        """
        This method will interpolate additional planes and create a new (!) HDF file.
        The new file will be stored in the case folder in a new folder called "interpolated_planes".
        The new file will get a name encoding the number of planes, e.g. "<casename>_intplanes.hdf".

        Parameters
        ----------
        z : array-like or int
            The z-coordinates of planes to be created or number of equally spaced planes between existing
            min/max values of z in measurement volume. If passing an integer, n-2 equally spaced planes are generated
            (-2 because outer-planes are excluded). Already existing planes are not re-computed. Similarly, the z-vector
            can include already existing planes. The coordinates must be within the measurement volume, not outside.
        only_time_averages : bool, optional=True
            Only interpolates the time-averaged data (Data in hdf group "timeAverages")
        method : bool, optional='linear'
            Interpolation method used by and passed to RegularGridInterpolator.
            Possible options: linear or nearest.

        Returns
        -------
        target_h5_filename : pathlib.Path
            File name to created hdf file.

        Notes
        -----
        A case file including existing and virtual datasets can be build with method: build_virtual_case_file.
        """

        if self.hdf_filename is None:
            raise FileExistsError(f'A multi-plane HDF file must exist. Convert multi-plane PIV to HDF first!')

        # getting x, y, z vectors (assuming planes coordinates dont change in time!)
        with h5py.File(self.hdf_filename) as h5:
            zvec = h5['z'][()]
            # tvec = h5['time'][()]
            xvec = h5['x'][()]
            yvec = h5['y'][()]

            xshape = h5['x'].shape

        # first do some user input checks:
        if isinstance(z, int):
            if zvec.min() == zvec.max():
                raise ValueError('All planes have the same z-coordinate. Impossible to generate intermediate planes')
            z = np.linspace(zvec.min(), zvec.max(), z)
        else:
            z = np.asarray(z)
            if z.ndim != 1:
                raise ValueError('You must specify the z locations of the planes via an 1d numpy array!')
            # only consider non existing z-locations:

        zinterp = np.array([_z for _z in z if _z not in zvec])
        if len(z) > len(zinterp):
            print(f'Reduced number planes to generate from {len(z)} to {len(zinterp)} '
                  'as some of the input planes already exist from the measurement.')
        target_h5_filename = pathlib.Path.joinpath(self.hdf_filename.parent,
                                                   f'{self.hdf_filename.stem}_interpolated_planes',
                                                   f'{self.hdf_filename.stem}_nplanes{len(zvec)}.hdf')

        if not target_h5_filename.parent.is_dir():
            pathlib.Path.mkdir(target_h5_filename.parent)

        # hard copy x,y,z,t and their attributes to interpolation hdf
        ixyzt_shape = list(xshape)
        ixyzt_shape[0] = len(zinterp)
        with h5py.File(target_h5_filename, 'w') as h5:
            h5.attrs['long_name'] = f'Interpolated planes of case {self.hdf_filename}'
            with h5py.File(self.hdf_filename) as h5m:
                for cname in ('x', 'y', 'ix', 'iy'):
                    ds = h5.create_dataset(cname, data=h5m[cname][:])
                    ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[cname])
                    core.copy_attributes(h5m[cname].attrs, ds)
            h5.create_dataset('z', data=zinterp)

            h5.create_group('timeAverages')
            with h5py.File(self.hdf_filename) as h5src:
                if not only_time_averages:
                    for ds_name, ds in h5src.items():
                        if isinstance(ds, h5py.Dataset) and ds.name not in ('/x', '/y', '/z', '/t', '/ix', '/iy'):
                            src_shape = list(ds.shape)
                            src_shape[0] = ixyzt_shape[0]
                            h5.create_dataset(ds_name, shape=src_shape)
                for ds_name, ds in h5src['timeAverages'].items():
                    if isinstance(ds, h5py.Dataset):
                        src_shape = list(ds.shape)
                        src_shape[0] = ixyzt_shape[0]
                        h5['timeAverages'].create_dataset(ds_name, shape=src_shape)

        xx, yy, zz = np.meshgrid(xvec, yvec, zinterp, indexing='ij')
        with h5py.File(target_h5_filename, 'r+') as h5trg:
            with h5py.File(self.hdf_filename) as h5src:
                print('interpolating...')

                interpolation_candidates = []
                if not only_time_averages:
                    for ds in h5src.values():
                        if isinstance(ds, h5py.Dataset):
                            if ds.name not in ('/x', '/y', '/z', '/t', '/ix', '/iy'):
                                interpolation_candidates.append(ds)
                for ds in h5src['timeAverages'].values():
                    if isinstance(ds, h5py.Dataset):
                        interpolation_candidates.append(ds)

                for ds in interpolation_candidates:
                    st_time = time.perf_counter()
                    if isinstance(ds, h5py.Dataset):
                        if ds.parent.name == '/':
                            raise NotImplementedError('Interpolating time data not supported yet')
                        else:  # datasets without time dimension
                            if ds.ndim == 4:
                                for icomp in range(ds.shape[-1]):
                                    interpolator = RegularGridInterpolator((xvec, yvec, zvec), ds[..., icomp],
                                                                           method=method)
                                    pts = np.stack((xx[...].ravel(), yy[...].ravel(), zz[...].ravel()),
                                                   axis=-1)
                                    h5trg[ds.name][..., icomp] = interpolator(pts).reshape(xx[...].shape).T
                            else:
                                interpolator = RegularGridInterpolator((xvec, yvec, zvec), ds[...].T, method=method)
                                _zz, _xx, _yy = np.meshgrid(zvec, xvec, yvec)
                                pts = np.stack((xx[...].ravel(), yy[...].ravel(), zz[...].ravel()),
                                               axis=-1)
                                h5trg[ds.name][...] = interpolator(pts).reshape(xx[...].shape).T
                    print(f'> {ds.name}: {(time.perf_counter() - st_time) * 1000:.2f} ms')
                print('...done.')
        return target_h5_filename

    def compute_intermediate_plane_using_delaunay(self, z: np.ndarray or int, ijth: int = 1,
                                                  only_time_averages: bool = True) -> pathlib.Path:
        """
        This method will interpolate additional planes and create a new (!) HDF file.
        The new file will be stored in the case folder in a new folder called "interpolated_planes".
        The new file will get a name encoding the number of planes, e.g. "<casename>_intplanes.hdf".

        Parameters
        ----------
        z : array-like or int
            The z-coordinates of planes to be created or number of equally spaced planes between existing
            min/max values of z in measurement volume. If passing an integer, n-2 equally spaced planes are generated
            (-2 because outer-planes are excluded). Already existing planes are not re-computed. Similarly, the z-vector
            can include already existing planes. The coordinates must be within the measurement volume, not outside.
        ijth : int, optional=1
            Reduces the number of interpolation source points. Only takes every ith/jth data point.
            Default is 1, thus takes all points and is highly recommended!
        only_time_averages : bool, optional=True
            Only interpolates the time-averaged data (Data in hdf group "timeAverages")

        Returns
        -------
        target_h5_filename : pathlib.Path
            File name to created hdf file.

        Notes
        -----
        A case file including existing and virtual datasets can be build with method: build_virtual_case_file.
        """

        if self.hdf_filename is None:
            raise FileExistsError(f'A multi-plane HDF file must exist. Convert multi-plane PIV to HDF first!')

        with h5py.File(self.hdf_filename, 'r') as h5:
            X = h5['x'][:, 0, ...]  # assuming planes coordinates dont change in time!
            Y = h5['y'][:, 0, ...]
            Z = h5['z'][:, 0, ...]

        xn = X[0, 0, :]
        yn = Y[0, :, 0]

        # first do some user input checks:
        if isinstance(z, int):
            z = np.linspace(Z.min(), Z.max(), z)
        else:
            z = np.asarray(z)
            if z.ndim != 1:
                raise ValueError('You must specify the z locations of the planes via an 1d numpy array!')
            # only consider non existing z-locations:

        zn = np.array([_z for _z in z if _z not in Z[:, 0, 0]])
        print(f'Reduced number planes to generate from {len(z)} to {len(zn)} '
              f'as some of the input planes already exist from the measurement.')

        # init 3d-grid:
        Xn, Yn, Zn = np.meshgrid(xn, yn, zn, indexing='ij')

        to_interpolate = list()
        dataset_identification = list()
        ii = 0
        with h5py.File(self.hdf_filename, 'r') as h5:
            xshape = h5['x'].shape  # for later use
            if not only_time_averages:
                # consider each time step!
                # may blow your RAM!
                # create Delaunay and then dynamically load datasets
                # then perform interpolation and then save to hdf. repeat.
                raise NotImplementedError()  # TODO interpolation for all time steps
            for key in h5['timeAverages'].keys():
                ds = h5['timeAverages'][key]
                if ds.ndim == 4:
                    for i in range(ds.shape[-1]):
                        dataset_identification.append([ds.name, ii, i, ds.shape])
                        to_interpolate.append(ds[:, ::ijth, ::ijth, i].ravel())
                        ii += 1
                else:
                    dataset_identification.append([ds.name, ii, -1, ds.shape])
                    to_interpolate.append(ds[:, ::ijth, ::ijth].ravel())
                    ii += 1

        target_h5_filename = pathlib.Path.joinpath(self.hdf_filename.parent,
                                                   f'{self.hdf_filename.stem}_interpolated_planes',
                                                   f'{self.hdf_filename.stem}_nplanes{len(zn)}.hdf')

        if not target_h5_filename.parent.is_dir():
            pathlib.Path.mkdir(target_h5_filename.parent)

        # hard copy x,y,z,t and their attributes to interpolation hdf
        ixyzt_shape = list(xshape)
        ixyzt_shape[0] = len(zn)
        with h5py.File(target_h5_filename, 'w') as h5:
            h5.attrs['long_name'] = f'Interpolated planes of case {self.hdf_filename}'
            with h5py.File(self.hdf_filename, 'r') as h5m:
                for cname in core.DIM_NAMES:
                    ds = h5.create_dataset(cname, shape=tuple(ixyzt_shape))
                    for i in range(len(zn)):
                        ds[i, ...] = h5m[cname][0, ...]
                    h5[cname].make_scale(core.DEFAULT_DATASET_LONG_NAMES[cname])
                    core.copy_attributes(h5m[cname].attrs, ds)
            # write z
            for iz, z in enumerate(zn):
                h5['z'][iz, ...] = z

        print('preparing to interpolate...')
        tri = qhull.Delaunay(np.stack((X[:, ::ijth, ::ijth].ravel(),
                                       Y[:, ::ijth, ::ijth].ravel(),
                                       Z[:, ::ijth, ::ijth].ravel())).T)

        # free some RAM:
        del X, Y, Z

        print('interpolating...')
        interpolator = LinearNDInterpolator(tri, np.stack(to_interpolate).T)
        interpolated_results = interpolator(Xn, Yn, Zn)
        print('...finished')

        print('writing data to hdf file...')
        with h5py.File(target_h5_filename, 'r+') as h5:
            with h5py.File(self.hdf_filename, 'r') as h5m:
                for di in dataset_identification:
                    ds_name, ds_result_idx, ds_var_idx, ds_orig_shape = di
                    new_shape = list(ds_orig_shape)
                    new_shape[0] = len(zn)
                    if ds_name not in h5:
                        ds = h5.create_dataset(ds_name, shape=new_shape)
                    else:
                        ds = h5[ds_name]
                    if ds_var_idx == -1:
                        ds[:] = interpolated_results.T[ds_result_idx, ...]
                    else:
                        ds[..., ds_var_idx] = interpolated_results.T[ds_result_idx, ...]

                    ds.dims[0].attach_scale(h5['z'])
                    for ic, c in zip((1, 2), (('y', 'iy'), ('x', 'ix'))):
                        ds.dims[ic].attach_scale(h5[c[0]])
                        ds.dims[ic].attach_scale(h5[c[1]])

                    # copy attributes
                    core.copy_attributes(h5m[ds_name].attrs, ds)

        print('...done writing.')
        return target_h5_filename

    def build_virtual_mplane_file(self, interpolated_planes_filename: pathlib.Path) -> pathlib.Path:
        """
        generates a new HDF file containing virtual datasets from
        (a) the original data
        and
        (b) the interpolated planes.
        In order to call this method, "compute_intermediate_plane()" must be called first,
        to generate such other file.

        Parameters
        ----------
        interpolated_planes_filename : pathlib.Path
            File name of the HDF file containing only (!) the interpolated planes.

        Returns
        -------
        virtual_hdf_filename : pathlib.Path
            The created HDF file with virtual datasets of all plane data.
        """
        # private notes:
        # currently only for timeAverages!!!!
        # 1. check if interpolated planes are actually in-between planes of this file
        #  -> this is taken care of when interpolated planes were created... a double-check is reasonable..
        # 2. check if interpolated planes have same dimensions
        #  -> see above, same reasoning
        # The virtual HDF file will only contain datasets from which interpolated datasets exist.
        # e.g. if only timeAverages-data was interpolated only those appear in the virtual dataset
        # of course x,y,z,t always exists
        # 3. build x,y,z,t VDS
        logger.info('Currently only implemented for data from group "timeAverages"')
        virtual_hdf_filename = pathlib.Path.joinpath(self.hdf_filename.parent, f'{self.hdf_filename.stem}.vhdf')
        with h5py.File(virtual_hdf_filename, 'w') as h5v:
            h5v.attrs['long_name'] = f'Virtual Case file containing virtual datasets from original measurement and ' \
                                     f'intermediate (interpolated) planes'
            h5v.create_group('timeAverages')
            layouts = dict()
            with h5py.File(interpolated_planes_filename) as h5i:  # h5 file of interpolated planes
                z_interp = h5i['z'][:]
                iz_interp = range(len(z_interp))
                nz_miplanes = len(iz_interp)
                false_list = [0] * len(z_interp)
            with h5py.File(self.hdf_filename) as h5m:  # h5 file of measurement planes
                z_meas = h5m['z'][:]
                iz_meas = range(len(z_meas))
                nz_meas = len(z_meas)
                true_list = [1] * len(z_meas)
                z_all = np.concatenate((z_meas, z_interp))  # all z-planes
                z_all_ismdata = [*true_list, *false_list]
                it_all = np.concatenate((iz_meas, iz_interp))
                isort = np.argsort(z_all[:])  # maybe turn z_all around if meas.-plane order is high to low
                plane_info = [(z_all_ismdata[ii], it_all[ii]) for ii in isort]
                nz = len(z_all)

                for k in ('x', 'y', 'ix', 'iy'):
                    ds = h5v.create_dataset(k, data=h5m[k][:])
                    core.copy_attributes(h5m[k].attrs, ds)
                ds = h5v.create_dataset('z', data=z_all[isort])
                core.copy_attributes(h5m['z'].attrs, ds)

                # create virtual datasets for all time-averaged data:
                for ds_name in h5m['timeAverages'].keys():
                    _ds_name = f'timeAverages/{ds_name}'
                    ds_attributes = h5m[_ds_name].attrs

                    # build Virtual layout
                    ds_shape = h5m[_ds_name].shape[1:]
                    vds_layout_shape = (nz, *ds_shape)

                    layouts[_ds_name] = h5py.VirtualLayout(shape=vds_layout_shape,
                                                           maxshape=vds_layout_shape,
                                                           dtype=h5m[_ds_name].dtype)

                    vsource_m = h5py.VirtualSource(self.hdf_filename, _ds_name,
                                                   shape=(nz_meas, *ds_shape))
                    vsource_p = h5py.VirtualSource(interpolated_planes_filename, _ds_name,
                                                   shape=(nz_miplanes, *ds_shape))

                    for ii, (ismdata, _iz) in enumerate(plane_info):
                        # fill virtual dataset with virtual source from real measurement
                        if ismdata:
                            layouts[_ds_name][ii, ...] = vsource_m[_iz, ...]
                        else:
                            layouts[_ds_name][ii, ...] = vsource_p[_iz, ...]
                    ds = h5v.create_virtual_dataset(_ds_name, layouts[_ds_name], fillvalue=0)
                    core.copy_attributes(ds_attributes, ds)
                    ds.dims[0].attach_scale(h5v['z'])
                    for ic, c in zip((1, 2), (('y', 'iy'), ('x', 'ix'))):
                        ds.dims[ic].attach_scale(h5v[c[0]])
                        ds.dims[ic].attach_scale(h5v[c[1]])
        return virtual_hdf_filename

    def to_vtk(self, vtk_filename_wo_suffix: pathlib.Path = None) -> Path:
        """converts the hdf file into vtk file. only considers time averages!

        Parameters
        ----------
        vtk_filename_wo_suffix : pathlib.Path
            File name without suffix to write vtk data to.

        Returns
        -------
        vtk_path: Path
        """
        super().to_vtk(vtk_filename_wo_suffix=vtk_filename_wo_suffix)

        data = vtk_utils.get_time_average_data_from_piv_case(self.hdf_filename)

        _, vtk_path = vtk_utils.result_3D_to_vtk(data, target_filename=str(self.vtk_file_name))
        return Path(vtk_path)

    def compute_magnitude_of_velocitys(self, overwrite=False):
        """computes the velocity magnitudes for each time step and for time averages"""
        with h5py.File(self.hdf_filename, 'r+') as h5:
            if self.one_freq_for_all_planes:
                iter_ls = (h5,)
            else:
                iter_ls = [h5[f'plane{iz:0{len(str(self.nz))}}'] for iz in range(self.nz)]

            for h5grp in iter_ls:
                if 'velmag' in h5grp and not overwrite:
                    raise KeyError('The dataset "velmag" already exists')
                if 'w' in h5grp:
                    mag = np.sqrt(h5grp['u'][:] ** 2 + h5grp['u'][:] ** 2 + h5grp['w'][:] ** 2)
                else:
                    mag = np.sqrt(h5grp['u'][:] ** 2 + h5grp['u'][:] ** 2)
                if 'velmag' not in h5grp:
                    ds_vel_mag = h5grp.create_dataset('velmag', shape=mag.shape,
                                                      compression=h5grp['z'].compression,
                                                      compression_opts=h5grp['z'].compression_opts)
                else:
                    ds_vel_mag = h5grp['velmag']
                ds_vel_mag[:] = mag
                ds_vel_mag.attrs['units'] = h5grp['u'].attrs['units']
                ds_vel_mag.attrs['standard_name'] = 'magnitude_of_velocity'
                if self.one_freq_for_all_planes:
                    ds_vel_mag.dims[0].attach_scale(h5grp['z'])
                    ds_vel_mag.dims[1].attach_scale(h5grp['time'])
                    ds_vel_mag.dims[2].attach_scale(h5grp['y'])
                    ds_vel_mag.dims[3].attach_scale(h5grp['x'])
                    ds_vel_mag.dims[2].attach_scale(h5grp['iy'])
                    ds_vel_mag.dims[3].attach_scale(h5grp['ix'])
                else:
                    ds_vel_mag.dims[0].attach_scale(h5grp['time'])
                    ds_vel_mag.dims[1].attach_scale(h5grp['y'])
                    ds_vel_mag.dims[2].attach_scale(h5grp['x'])
                    ds_vel_mag.dims[1].attach_scale(h5grp['iy'])
                    ds_vel_mag.dims[2].attach_scale(h5grp['ix'])

            # mag_av = np.nanmean(mag, axis=1)
            # if 'velmag' not in h5grp['timeAverages']:
            #     ds_vel_mag_av = h5grp['timeAverages'].create_dataset('velmag', shape=mag_av.shape,
            #                                                       compression=h5grp['z'].compression,
            #                                                       compression_opts=h5grp['z'].compression_opts)
            # else:
            #     ds_vel_mag_av = h5grp['timeAverages']['velmag']
            # ds_vel_mag_av[:] = mag_av
            # ds_vel_mag_av.attrs['units'] = h5grp['u'].attrs['units']
            # ds_vel_mag_av.attrs['standard_name'] = 'magnitude_of_velocity'

    def compute_gradz(self, incompressible: bool = False):
        """computes the gradient d()/dz if not already exists in HDF file and adds as dataset
        For incompressible 2d flows dwdz is computed from continuity equation is incompressible==True

        Parameters
        ----------
        incompressible: bool, optional=False
            bla


        """
        if self.hdf_filename is not None and not self.hdf_filename.exists():
            raise FileNotFoundError('No HDF file found')
        with h5py.File(self.hdf_filename, 'r+') as h5:
            velocity = h5['velocity'][:]
            if np.all(velocity[..., 2] == 0):
                print('The w-velocity is zero everywhere, not computing dwdz from velocity vector!')
                icomp = 2
                grad_name_list = ('dudz', 'dvdz')
                grad_standard_name_list = ('z_derivative_of_x_velocity',
                                           'z_derivative_of_y_velocity')
            else:
                icomp = 3
                grad_name_list = ('dudz', 'dvdz', 'dwdz')
                grad_standard_name_list = ('z_derivative_of_x_velocity',
                                           'z_derivative_of_y_velocity',
                                           'z_derivative_of_z_velocity')
            dz = (h5['z'][:].max() - h5['z'][:].min()) / (h5['z'].shape[0] - 1)
            gradient_z = np.gradient(h5['velocity'][..., 0:icomp], dz, axis=0)  # 4 is abs vel, don't take!

            grad_shape = gradient_z[..., 0].shape
            _chunks = h5['velocity'].chunks[:-1]
            _maxshape = h5['velocity'].maxshape[:-1]
            for igrad, grad_name, std_name in zip(enumerate(grad_name_list), grad_standard_name_list):
                if grad_name not in h5:
                    ds = h5.create_dataset(grad_name, shape=grad_shape,
                                           data=gradient_z[..., igrad],
                                           maxshape=_maxshape,
                                           chunks=_chunks,
                                           compression=self.configuration['compression'],
                                           compression_opts=self.configuration['compression_opts'])
                    ds.attrs["unit"] = h5['dudx'].attrs['unit']
                    ds.attrs["standard_name"] = std_name
                    for ic, c in enumerate(('z', 'time', 'y', 'x')):
                        ds.dims[ic].attach_scale(h5[c])
                    ds.dims[2].attach_scale(h5['iy'])
                    ds.dims[3].attach_scale(h5['ix'])

            if icomp == 3 and incompressible:
                if 'dwdz' not in h5 and 'dudx' in h5 and 'dvdy' in h5:
                    dwdz = compute_z_derivative_of_z_velocity(h5["dudx"], h5["dvdy"])
                    _maxshape = list(dwdz.shape)
                    _maxshape[0] = None
                    _chunks = list(dwdz.shape)
                    _chunks[0] = 1
                    ds = h5.create_dataset("dwdz", shape=dwdz.shape, data=dwdz,
                                           maxshape=_maxshape,
                                           chunks=tuple(_chunks),
                                           compression=self.configuration['compression'],
                                           compression_opts=self.configuration['compression_opts'])
                    ds.attrs["unit"] = h5['dudx'].attrs['unit']
                    ds.attrs["standard_name"] = 'z_derivative_of_z_velocity'
                    # attach scale
                    for ic, c in enumerate(('z', 'time', 'y', 'x')):
                        ds.dims[ic].attach_scale(h5[c])
                    ds.dims[2].attach_scale(h5['iy'])
                    ds.dims[3].attach_scale(h5['ix'])

    def remove_nc_files(self):
        """Removes all nc files of all snapshots in all planes"""
        for p in self.planes:
            for nc_file in p._found_nc_files:
                nc_file.unlink(missing_ok=True)


def multiplane_from_average_dat_files(plane_folders: List[pathlib.Path], target: pathlib.Path) -> pathlib.Path:
    """Converts average dat files into single HDF file and returns path to that file.

    Parameters
    ----------
    plane_folders : List[pathlib.Path]
        List of directory paths to planes.
    target : Path
        Case HDF file name to store data at.

    Returns
    -------
    target : Path
        Case HDF file name where data is stored.
    """
    _plane_folders = [Path(_plane) for _plane in plane_folders]
    nz = len(_plane_folders)
    plane_hdf_files = []
    for plane_folder in _plane_folders:
        avg_dat_file = [d for d in plane_folder.glob('*avg.dat')][0]
        reyn_dat_file = [d for d in plane_folder.glob('*reyn.dat')][0]
        rms_dat_file = [d for d in plane_folder.glob('*rms.dat')][0]

        plane_hdf_file = pathlib.Path(f'{plane_folder.parent}/{plane_folder.name}.hdf')
        plane_hdf_files.append(plane_hdf_file)

        plane.build_plane_hdf_from_average_dat_files(avg_dat_file=avg_dat_file,
                                                     reyn_dat_file=reyn_dat_file,
                                                     rms_dat_file=rms_dat_file,
                                                     target=plane_hdf_file)

    with h5py.File(target, mode='w') as h5:

        gav = h5.create_group('timeAverages')

        with h5py.File(plane_hdf_files[0]) as h5plane:
            nx = h5plane['x'].size
            ny = h5plane['y'].size

            for dn in ('x', 'y', 'ix', 'iy'):
                ds = h5.create_dataset(dn, data=h5plane[dn][()])
                ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES[dn])
                ds.attrs['units'] = h5plane[dn].attrs['units']
                ds.attrs['standard_name'] = pivview_to_standardnames_dict[dn]
            ds = h5.create_dataset('z', shape=(nz,))
            ds.make_scale(core.DEFAULT_DATASET_LONG_NAMES['z'])
            ds.attrs['units'] = h5plane[dn].attrs['units']
            ds[0] = h5plane['z'][()]
            ds.attrs['standard_name'] = pivview_to_standardnames_dict['z']

            for plane_ds_name, plane_ds in h5plane['timeAverages'].items():
                ds = gav.create_dataset(plane_ds_name, shape=(nz, ny, nx))
                ds[0, ...] = plane_ds[()]

                ds.attrs['units'] = plane_ds.attrs['units']
                ds.attrs['long_name'] = plane_ds.attrs['long_name']

                for idim, dn in enumerate(('z', 'y', 'x')):
                    ds.dims[idim].attach_scale(h5[dn])
                ds.dims[1].attach_scale(h5['iy'])
                ds.dims[2].attach_scale(h5['ix'])

        for iplane, plane_hdf_file in enumerate(plane_hdf_files[1:]):
            iz = iplane + 1
            with h5py.File(plane_hdf_file, 'r') as h5plane:
                h5['z'][iz] = h5plane['z'][()]

                for plane_ds_name, plane_ds in h5plane['timeAverages'].items():
                    gav[plane_ds_name][iz, ...] = plane_ds[:]
        update_standard_names(h5['/'])
    for plane_hdf_file in plane_hdf_files:
        pathlib.Path.unlink(plane_hdf_file)

    return target


def build_plane_hdf_from_average_dat_files(avg_dat_file: pathlib.Path, rms_dat_file: pathlib.Path,
                                           reyn_dat_file: pathlib.Path,
                                           target: pathlib.Path) -> pathlib.Path:
    """Generates a Plane HDF file from average files. Data is stored in
    in group "timeAverages". Datasets "x", "y" and "z" (not "t"!) are created at root level.
    """
    target = pathlib.Path(target)

    if avg_dat_file is not None:
        avg_hdf = PIVSnapshotDatFile(avg_dat_file).convert(target_hdf_filename=touch_tmp_hdf5_file())
    else:
        avg_hdf = None

    # rms file has the vector positions in pixel units! avg and reyn have real units only!
    if rms_dat_file is not None:
        rms_hdf = PIVSnapshotDatFile(rms_dat_file).convert(target_hdf_filename=touch_tmp_hdf5_file())
    else:
        rms_hdf = None

    if reyn_dat_file is not None:
        reyn_hdf = PIVSnapshotDatFile(reyn_dat_file).convert(target_hdf_filename=touch_tmp_hdf5_file())
    else:
        reyn_hdf = None

    with h5py.File(target, mode='w') as h5:
        # x,y,z is taken from h5avg
        gav = h5.create_group('timeAverages')

        with h5py.File(avg_hdf) as h5avg:
            nx = h5avg['x'].size
            ny = h5avg['y'].size
            shape = (ny, nx)

            for dn in ('y', 'x', 'z'):
                h5.copy(h5avg[dn], h5['/'], dn)
                if 'CLASS' in h5[dn].attrs:
                    del h5[dn].attrs['CLASS']
                if 'NAME' in h5[dn].attrs:
                    del h5[dn].attrs['NAME']
                if 'REFERENCE_LIST' in h5[dn].attrs:
                    del h5[dn].attrs['REFERENCE_LIST']
                if dn != 'z':
                    h5[dn].make_scale(core.DEFAULT_DATASET_LONG_NAMES[dn])

        if rms_hdf:
            # get ix, iy from rms
            with h5py.File(rms_hdf) as h5rms:
                nx = h5rms['x'].size
                ny = h5rms['y'].size
                shape = (ny, nx)
                for dn in (('iy', 'y'), ('ix', 'x')):
                    h5.copy(h5rms[dn[1]], h5['/'], dn[0])
                    if 'CLASS' in h5[dn[0]].attrs:
                        del h5[dn[0]].attrs['CLASS']
                    if 'NAME' in h5[dn[0]].attrs:
                        del h5[dn[0]].attrs['NAME']
                    if 'REFERENCE_LIST' in h5[dn[0]].attrs:
                        del h5[dn[0]].attrs['REFERENCE_LIST']
                    h5[dn[0]].make_scale(core.DEFAULT_DATASET_LONG_NAMES[dn[0]])

        for hdf_file in (avg_hdf, rms_hdf, reyn_hdf):
            if hdf_file:
                with h5py.File(hdf_file) as _h5:
                    for key in _h5.keys():
                        if key not in core.DIM_NAMES:
                            if key not in gav:
                                ds = gav.create_dataset(key, shape=shape)
                                ds[:] = _h5[key][:]
                                ds.attrs['units'] = _h5[key].attrs['units']
                                ds.attrs['long_name'] = _h5[key].attrs['long_name']
                                for ic, dn in enumerate(('y', 'x')):
                                    ds.dims[ic].attach_scale(h5[dn])
                                if 'iy' in h5:
                                    ds.dims[0].attach_scale(h5['iy'])
                                if 'ix' in h5:
                                    ds.dims[1].attach_scale(h5['ix'])
                                ds.attrs['COORDINATES'] = ['/z', ]

    if avg_hdf:
        pathlib.Path.unlink(avg_hdf)
    if rms_hdf:
        pathlib.Path.unlink(rms_hdf)
    if reyn_hdf:
        pathlib.Path.unlink(reyn_hdf)

    return target


#  Aliases
MPlane = PIVMultiPlane
