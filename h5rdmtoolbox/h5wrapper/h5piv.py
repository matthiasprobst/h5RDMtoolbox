import json
import logging
import warnings
from pathlib import Path
from typing import List, Callable

import h5py
import numpy as np
from pint_xarray import unit_registry as ureg

from .h5base import config
from .h5flow import H5Flow, H5FlowLayout, FrozenDataset
from .h5flow import VectorInterface
from .. import utils, user_data_dir
from ..conventions.standard_names import PIVConvention
from ..x2hdf import piv2hdf
from ..x2hdf.piv2hdf.par import PivViewParFile

logger = logging.getLogger(__package__)

# software name (key) and alias for it (values)  (all lowercase!)
SUPPORTED_PIV_SOFTWARE = {'pivview': ('pivtec pivview', 'pivview'), 'lavision': ('davis',)}


def _check_piv_software(software_name):
    """Returns the common name of the software if in SUPPORTED_PIV_SOFTWARE
    otherwise returns False"""
    if software_name is not None:
        software_name_lower = software_name.lower()
        for av_software_name, av_software_alias in SUPPORTED_PIV_SOFTWARE.items():
            for alias in av_software_alias:
                if alias in software_name_lower:
                    return av_software_name
        print(utils._failtext(f'{software_name} not in list of supported piv software. '
                              'Please check that there is no spelling mistake. '
                              'Otherwise, please open an issue for it.\n'
                              f'Supported software: {list(SUPPORTED_PIV_SOFTWARE.keys())}'))
    else:
        logger.warning(utils._failtext('Software not set as attribute in File!'))
    return False


class XRUncertaintyDataset(FrozenDataset):
    """
    xarray Dataset for uncertaint computation based on displacement or velocity field.
    """

    __slots__ = ()

    def compute_uncertainty(self, method: Callable, *args, **kwargs):
        """computes the uncertainty using the passed method"""
        return method(self, *args, **kwargs)


class H5PIVLayout(H5FlowLayout):

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
        with h5py.File(self.layout_file, mode='r+') as h5:
            # grsetup = h5.create_group(name='Setup')
            # grpeq = grsetup.create_group(name='Equipment')
            # grpeq.create_group('Camera')
            # grpeq.create_group('Laser')
            #
            # _ = h5.create_group(name='Acquisition')
            # h5.create_group(name='Acquisition/Raw')
            # h5.create_group(name='Acquisition/Processed')
            # h5.create_group(name='Acquisition/Calibration')

            h5.attrs['title'] = '__The common name of the file that might ' \
                                'better explain it by a short string'

            # ds_vel = h5.create_dataset('x', shape=(1,))
            ds_vel = h5['x']
            ds_vel.attrs['units'] = 'm'
            ds_vel.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
            ds_vel.attrs['standard_name'] = 'x_coordinate'

            # ds_vel = h5.create_dataset('y', shape=(1,))
            ds_vel = h5['y']
            ds_vel.attrs['units'] = 'm'
            ds_vel.attrs['__ndim__'] = 1  # (nz, nt, ny, nx, nv)
            ds_vel.attrs['standard_name'] = 'y_coordinate'

            ds_ix = h5.create_dataset('ix', shape=(1,))
            ds_iy = h5.create_dataset('iy', shape=(1,))

            for ds in (ds_ix, ds_iy):
                ds.attrs['units'] = 'm'
                ds.attrs['__ndim__'] = (0, 1)
                ds_vel.attrs['standard_name'] = f'{ds_ix.name[1:]}_pixel_coordinate'

            # ds_vel = h5.create_dataset('z', shape=(1,))
            ds_vel = h5['z']
            ds_vel.attrs['units'] = 'm'
            ds_vel.attrs['__ndim__'] = (0, 1)  # (nz, nt, ny, nx, nv)
            ds_vel.attrs['standard_name'] = 'z_coordinate'

            ds_vel = h5.create_dataset('u', shape=(1,))
            ds_vel.attrs['units'] = 'm/s'
            ds_vel.attrs['__ndim__'] = (2, 3, 4)  # (nz, nt, ny, nx, nv)
            ds_vel.attrs['standard_name'] = 'x_velocity'

            ds_vel = h5.create_dataset('v', shape=(1,))
            ds_vel.attrs['units'] = 'm/s'
            ds_vel.attrs['__ndim__'] = (2, 3, 4)  # 4: (nz, nt, ny, nx, nv)
            ds_vel.attrs['standard_name'] = 'y_velocity'


class H5PIV(H5Flow):
    Layout: H5PIVLayout = H5FlowLayout(Path.joinpath(user_data_dir, f'layout/H5PIV.hdf'))

    @property
    def timesteps(self):
        return self['x'].shape[1]

    @property
    def nplanes(self):
        return self['x'].shape[0]

    @property
    def extent(self):
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
    def software(self):
        """Returns attribute 'software'"""
        if 'software' in self.attrs:
            return self.attrs.get('software')
        else:
            return self.attrs['pivview_parameters'].get('software')

    @software.setter
    def software(self, software_name):
        common_software_name = _check_piv_software(software_name)
        if common_software_name:
            if software_name is not None:
                self.attrs['software'] = software_name
        else:
            raise ValueError(f'"{software_name}" is not an unknown software')

    @property
    def final_interrogation_window_size(self):
        common_software_name = _check_piv_software(self.software)
        if common_software_name == 'pivview':
            if 'interrogation_window_size' in self.attrs:
                return np.asarray(self.attrs['interrogation_window_size'])
            elif 'ev_IS_size_x' in self.attrs:
                return np.array([self.attrs['ev_IS_size_x'], self.attrs['ev_IS_size_y'], self.attrs['ev_IS_size_z']])
            elif 'pivview_parameters' in self.attrs:
                pivview_parameters = self.attrs['pivview_parameters']

                if isinstance(pivview_parameters, str):
                    pivview_parameters = json.loads(pivview_parameters)
                return np.array([pivview_parameters['ev_IS_size_x'], pivview_parameters['ev_IS_size_y'],
                                 pivview_parameters['ev_IS_size_z']])

    @property
    def final_window_size(self):
        # alias for final_interrogation_window_size
        return self.final_interrogation_window_size

    @property
    def window_size(self):
        # alias for final_interrogation_window_size
        return self.final_interrogation_window_size

    @property
    def interrogation_window_overlap(self):
        common_software_name = _check_piv_software(self.software)
        if common_software_name == 'pivview':
            if 'interrogation_window_overlap' in self.attrs:
                return self.attrs['interrogation_window_overlap']
            elif 'ev_multigrid_step_x' in self.attrs:
                multigrid_wins = self.attrs['ev_multigrid_win_x'], self.attrs['ev_multigrid_win_y']
                multigrid_steps = self.attrs['ev_multigrid_step_x'], self.attrs['ev_multigrid_step_y']
                return multigrid_steps[0] / multigrid_wins[0], multigrid_steps[1] / multigrid_wins[1]
            elif 'pivview_parameters' in self.attrs:
                pivview_parameters = self.attrs['pivview_parameters']
                if isinstance(pivview_parameters, str):  # str-dictionary
                    pivview_parameters = json.loads(pivview_parameters)
                multigrid_wins = pivview_parameters['ev_multigrid_win_x'], pivview_parameters['ev_multigrid_win_y']
                multigrid_steps = pivview_parameters['ev_multigrid_step_x'], pivview_parameters['ev_multigrid_step_y']
                return multigrid_steps[0] / multigrid_wins[0], multigrid_steps[1] / multigrid_wins[1]

    @property
    def window_overlap(self):
        """alias of interrogation_window_overlap"""
        return self.interrogation_window_overlap

    @property
    def overlap(self):
        """alias of interrogation_window_overlap"""
        return self.interrogation_window_overlap

    @property
    def evaluation_method(self):
        common_software_name = _check_piv_software(self.software)
        if common_software_name == 'pivview':
            if 'evaluation_method' in self.attrs:
                return self.attrs['evaluation_method']
            elif 'ev_method' in self.attrs:
                return self.attrs['ev_method']
            elif 'pivview_parameters' in self.attrs:
                pivview_parameters = self.attrs['pivview_parameters']
                return pivview_parameters['ev_method']

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

    def compute_uncertainty(self, displacement_dataset: VectorInterface, method: Callable, *args, **kwargs):
        return displacement_dataset(method, *args, **kwargs)

    @property
    def DisplacementVector(self):
        return self.get_vector(standard_names=('x_displacement', 'y_displacement'),
                               xrcls=XRUncertaintyDataset)

    @property
    def VelocityVector(self):
        return self.get_vector(standard_names=('x_velocity', 'y_velocity'),
                               xrcls=XRUncertaintyDataset)

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

    def get_piv_parameters(self, iz=0) -> PivViewParFile:
        """Returns an instance of PivViewParFle. It looks for the parameter dictionary depending on the
        data structure:
        - z-coordinate is 0D: It is a PIV plane and piv_parameter dictionary is stored in the root attributes
        - z-coordinate is 1D: There is a piv_parameter group at root level with a parameter dictionary for each plane

        As HDF files cannot store dictionares, the parameters are stred as a string-representation of a dictionary
        (json.dumps()"""
        piv_software = self.software
        if 'pivview' in piv_software.lower():
            par = PivViewParFile()
            if 'piv_parameters' in self.attrs:
                par.read_dict(self.attrs['piv_parameters'])
            elif 'piv_parameters' in self:
                par.read_dict(self['piv_parameters'].attrs[f'plane{iz}'])
            return par
        else:
            raise NotImplementedError(f'H5PIV currently ony supports PivTec PIVview')

    def __init__(self, name=None, mode="r+", title=None, sn_convention=None,
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
        if sn_convention is None:
            sn_convention = PIVConvention
        super(H5PIV, self).__init__(name=name, mode=mode, title=title,
                                    sn_convention=sn_convention, **kwargs)
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
        dwdz = compute_dwdz(dudx[:].pint.quantify(), dvdy[:].pint.quantify())
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
                vdp_data[iz, it, 0, 0] = vdp(piv_flags=piv_flags[iz, it, :, :], flag_valid=flag_valid,
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
        return self._compute_running_statistics(statistics.running_mean,
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
        return self._compute_running_statistics(statistics.running_std,
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
        data = piv2hdf.vtk_utils.get_time_average_data_from_piv_case(self.filename)
        _, vtk_path = piv2hdf.vtk_utils.result_3D_to_vtk(
            data, target_filename=_vtk_filename)
        return vtk_path
