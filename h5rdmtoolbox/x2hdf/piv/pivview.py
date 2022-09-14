import configparser
import json
import pathlib
from os import environ
from pathlib import Path
from typing import Dict, Tuple

import h5py
import numpy as np

from .interface import PIVFile, PIV_PARAMETER_GRP_NAME, PIVParameterInterface
from .nc import process_pivview_nc_data

try:
    from netCDF4 import Dataset as ncDataset
except ImportError:
    raise ImportError('Package netCDF4 is not installed. Either install it '
                      'separately or install the repository with pip install h5RDMtolbox [piv]')

try:
    NCDF2PAR = Path(environ.get('ncdf2par'))
except TypeError:
    NCDF2PAR = None

PIVVIEW_SOFTWARE_NAME = 'pivview'

DIM_NAMES = ('z', 'time', 'y', 'x', 'ix', 'iy')
DIM_NAMES_TIMEAVERAGED = ('z', 'y', 'x', 'ix', 'iy')
DEFAULT_DATASET_LONG_NAMES = {'x': 'x-coordinate',
                              'y': 'y-coordinate',
                              'z': 'z-coordinate',
                              'ix': 'x-pixel-coordinate',
                              'iy': 'y-pixel-coordinate',
                              'time': 'time'}
IGNORE_ATTRS = ('mean_dx', 'mean_dy', 'mean_dz',
                'rms_dx', 'rms_dy', 'rms_dz',
                'coord_min', 'coord_max', 'coord_units', 'time_step', 'time_step_idx',
                'CLASS', 'NAME', 'DIMENSION_LIST', 'REFERENCE_LIST', 'COORDINATES')

MULTIPLANE_TITLE = 'PIV multi-plane file generated from PIVview netCDF4 files.'
PIVPLANE_TITLE = 'PIV plane file generated from PIVview netCDF4 files.'
PIVSNAPSHOT_TITLE = 'PIV snapshot file generated from a single PIVview netCDF4 file.'

PIV_FILE_TYPE_NAME = {'PIVSnapshot': 'snapshot',
                      'PIVPlane': 'single_plane',
                      'PIVMultiPlane': 'multi_plane'}


class PIVviewParameterFile(PIVParameterInterface):
    """Parameter file interface for PIVview"""

    def __init__(self, filename):
        super().__init__(filename)
        _cfg = configparser.ConfigParser()
        _cfg.read(filename)
        self.param_dict = {}
        for s in _cfg.sections():
            self.param_dict[s.strip('-').strip(' ')] = {k: eval(v) for k, v in dict(_cfg[s]).items()}

    def save(self, filename: pathlib.Path):
        """Save to original file format"""
        _cfg = configparser.ConfigParser()
        _cfg.read_dict(self.param_dict)
        with open(filename, 'w') as f:
            _cfg.write(f)

    def from_hdf(self, grp: h5py.Group) -> None:
        """Read fro HDF group"""
        pass

    @staticmethod
    def from_dir(dirname):
        """reads parameter from dirname and returns instance of this class"""
        pars = list(dirname.glob(f'*{PIVviewParameterFile.suffix}'))
        if len(pars) != 1:
            raise FileExistsError('Cannot find parameter file')
        return PIVviewParameterFile(pars[0])


class PIVviewFlag:
    """PIV Flag class"""
    _hex_dict = {"inactive": "0x0", "active": "0x1", "masked": "0x2",
                 "noresult": "0x4", "disabled": "0x8", "filtered": "0x10",
                 "interpolated": "0x20", "replaced": "0x40", "manualedit": "0x80"}

    _dict_int = {k: int(v, 16) for k, v in _hex_dict.items()}

    def __init__(self, value: int) -> None:
        self.value = value
        self.flag_meaning = {0: 'inactive',
                             1: 'active',
                             2: 'masked',
                             4: 'noresult',
                             8: 'disabed'}

    def __str__(self) -> str:

        for (k1, v1) in self._dict_int.items():
            if v1 == self.value:
                return k1

        for (k1, v1) in self._dict_int.items():
            for (k2, v2) in self._dict_int.items():
                if v1 + v2 == self.value and v1 != v2:
                    return "%s+%s" % (k1, k2)

        for (k1, v1) in self._dict_int.items():
            for (k2, v2) in self._dict_int.items():
                for (k3, v3) in self._dict_int.items():
                    if v1 + v2 + v3 == self.value and v1 != v2:
                        return "%s+%s+%s" % (k1, k2, k3)

        raise RuntimeError(f'Cannot interpret flag value {self.value}')


class PIVViewNcFile(PIVFile):
    """Interface class to a PIVview netCDF4 file"""
    suffix: str = '.nc'
    parameter = PIVviewParameterFile
    _parameter: PIVviewParameterFile = None

    # def __init__(self, filename: pathlib.Path, parameter_filename: Union[None, pathlib.Path] = None):
    #     super().__init__(filename, parameter_filename)
    #     if self._parameter_filename is None:
    #         self._parameter_filename = self.parameter_filename

    def read(self, config, recording_time: float, build_coord_datasets=True) -> Tuple[Dict, Dict, Dict]:
        """reads and processes nc data"""
        masking = config['masking']
        interpolation = config['interpolation']
        apply_mask = config['apply_mask']
        z_source = config['z_source']
        nc_data, nc_root_attr, nc_variable_attr = process_pivview_nc_data(self.filename, z_source=z_source,
                                                                          timestep=recording_time,
                                                                          masking=masking,
                                                                          interpolate=interpolation,
                                                                          apply_mask=apply_mask,
                                                                          build_coord_datasets=build_coord_datasets,
                                                                          standardized_name_table_translation=config[
                                                                              'standardized_name_table_translation'])
        # nc_root_attr['filename'] = nc_root_attr.pop('long_name')
        unique_flags = np.unique(nc_data['piv_flags'][:])
        nc_variable_attr['piv_flags']['flag_meaning'] = json.dumps(
            {str(PIVviewFlag(u)): int(u) for u in unique_flags})
        return nc_data, nc_root_attr, nc_variable_attr

    # @property
    # def parameters(self) -> Union[PivViewParFile, PivViewConfigFile]:
    #     """Return a PivViewParFile"""
    #     if self._parameter_filename is None:
    #         self._parameter_filename = self.parameter_filename
    #     if self._parameter_filename.suffix == '.par':
    #         parobj = PivViewParFile()
    #     else:
    #         parobj = PivViewConfigFile()
    #     parobj.read(self._parameter_filename)
    #     return parobj

    # @property
    # def parameter_filename(self) -> pathlib.Path:
    #     """Return a piv parameter filename (.par or .cfg)"""
    #     working_dir = self.filename.parent
    #     parameter_files = list(working_dir.glob('*.par'))
    #     config_files = list(working_dir.glob('*.cfg'))
    #     if len(parameter_files) == 1 and len(config_files) == 0:
    #         return parameter_files[0]
    #     if len(parameter_files) == 0 and len(config_files) == 1:
    #         return config_files[0]
    #     if len(parameter_files) == 0 and len(config_files) == 0:
    #         raise FileExistsError(f'No parameter file found here: {self.filename.parent}')
    #     if len(parameter_files) > 0 and len(config_files) > 0:
    #         raise FileExistsError(f'Too many files: Parameter file and config file found here: {self.filename.parent}')

    # def write_parameters(self, param_grp: h5py.Group):
    #     """writes piv parameters to an opened and existing param_grp"""
    #     parobj = self.parameters
    #     parobj.to_hdf_group(param_grp)
    #     param_grp.attrs['dict'] = json.dumps(parobj.to_dict())

    def to_hdf(self, hdf_filename: pathlib.Path,
               config: Dict, recording_time: float) -> pathlib.Path:
        """converts the snapshot into an HDF file"""
        nc_data, nc_root_attr, nc_variable_attr = self.read(config, recording_time)
        ny, nx = nc_data['y'].size, nc_data['x'].size
        # building HDF file
        if hdf_filename is None:
            _hdf_filename = Path.joinpath(self.name.parent, f'{self.name.stem}.hdf')
        else:
            _hdf_filename = hdf_filename
        with h5py.File(_hdf_filename, "w") as main:
            main.attrs['plane_directory'] = str(self.filename.parent.resolve())
            main.attrs['software'] = PIVVIEW_SOFTWARE_NAME
            main.attrs['title'] = 'piv snapshot data'

            # process piv_parameters. there must be a parameter file at the parent location
            piv_param_grp = main.create_group(PIV_PARAMETER_GRP_NAME)
            self.write_parameters(piv_param_grp)

            for i, cname in enumerate(('x', 'y', 'ix', 'iy')):
                ds = main.create_dataset(
                    name=cname, shape=nc_data[cname].shape,
                    maxshape=nc_data[cname].shape,
                    chunks=nc_data[cname].shape,
                    data=nc_data[cname], dtype=nc_data[cname].dtype,
                    compression=config['compression'],
                    compression_opts=config['compression_opts'])
                for k, v in nc_variable_attr[cname].items():
                    ds.attrs[k] = v
                ds.make_scale(DEFAULT_DATASET_LONG_NAMES[cname])

            for i, cname in enumerate(('z', 'time')):
                ds = main.create_dataset(cname, data=nc_data[cname])
                for k, v in nc_variable_attr[cname].items():
                    ds.attrs[k] = v
                ds.make_scale(DEFAULT_DATASET_LONG_NAMES[cname])

            # Data Arrays
            _shape = (ny, nx)
            for k, v in nc_data.items():
                if k not in DIM_NAMES:
                    ds = main.create_dataset(
                        name=k, shape=_shape, dtype=v.dtype,
                        maxshape=_shape,
                        chunks=_shape,
                        compression=config['compression'],
                        compression_opts=config['compression_opts'])
                    ds[:] = v
                    for ic, c in enumerate((('y', 'iy'), ('x', 'ix'))):
                        ds.dims[ic].attach_scale(main[c[0]])
                        ds.dims[ic].attach_scale(main[c[1]])
                    ds.attrs['COORDINATES'] = ['time', 'z']

                    if k in nc_variable_attr:
                        for attr_key, attr_val in nc_variable_attr[k].items():
                            if attr_key not in IGNORE_ATTRS:
                                ds.attrs[attr_key] = attr_val
            # # pivflags explanation:
            # unique_flags = np.unique(main['piv_flags'][:])
            # main['piv_flags'].attrs['flag_meaning'] = json.dumps(
            #     {str(PIVviewFlag(u)): int(u) for u in unique_flags})
        return hdf_filename
