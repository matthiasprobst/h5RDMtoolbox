import configparser
import json
import pathlib
import subprocess
import tempfile
from os import environ
from pathlib import Path
from typing import Dict, Tuple

import h5py
import numpy as np

from .interface import PIVFile, PIV_PARAMETER_GRP_NAME, PIVParameterInterface
from .nc import process_pivview_nc_data
from ..._repr import make_bold

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


def _is_nc_file(nc_filename: Path):
    """tries to open a nc file and returns success"""
    try:
        with ncDataset(nc_filename, 'r') as nc_rootgrp:
            _ = nc_rootgrp.dimensions
            return True
    except OSError:
        return False


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
            self._cfg.write(f)

    # def to_hdf(self, grp: h5py.Group) -> Dict:
    #     """Convert to HDF group"""

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


class PivViewParFile(configparser.ConfigParser):
    filename: Path = None
    header_line: str = ''
    header: str or None = None

    optionxform = str  # otherwise makes items lowercase

    def __str__(self):
        out_str = ''
        for k in self.sections():
            out_str += make_bold(f'\n{k.strip(" ").strip("-").strip()}')
            for item in self.items(k):
                try:
                    out_str += f'\n\t{item[0]}: {eval(item[1])}'
                except:
                    out_str += f'\n\t{item[0]}: {item[1]}'
        return out_str

    def aliasitems(self, alias_section_name):
        """Section names might be very long. By providing a sub string of a existing
        section name (called alias_section_name) self.items() is called with the found
        match"""
        for section in self.sections():
            if alias_section_name in section:
                return self.items(section)
        return None

    def read_nc(self, nc_filename: Path, ncdf2par: Path = None) -> None:
        """inits a pivview parameter file from a netCDF4 file. Therefore calls ncdf2par to create ascii parameter
        file which is then read as used to"""
        self.__init__()  # init empty ConfigParserFile
        # call ncdf2par to create ascii file:
        if ncdf2par is not None:  # user defines exe via method argument
            ncdf2par_exe = ncdf2par
        else:
            ncdf2par_exe = NCDF2PAR

        if ncdf2par_exe is None or not ncdf2par_exe.exists():
            raise FileExistsError(f'Could not find exe "ncdf2par" here: "{ncdf2par_exe}"')
        tmp_name = Path(next(tempfile._get_candidate_names()))
        tmp_filename = Path.joinpath(Path(tempfile.gettempdir()), tmp_name)
        cmd = [str(ncdf2par_exe), str(nc_filename), str(tmp_filename)]
        subprocess.run(cmd)
        if tmp_filename.exists():
            self.read(tmp_filename)
        else:
            raise RuntimeError('It seems that ncdf2par failed. No parameter file read. Subprocess was called '
                               'with the following arg list: '
                               f'"{cmd}"')

    def read(self, filenames: Path, encoding=None):
        if isinstance(filenames, list) or isinstance(filenames, tuple):
            raise ValueError(f'Only one config/parameter file accepted!')
        self.filename = filenames
        if _is_nc_file(filenames):
            return self.read_nc(filenames)

        with open(filenames, 'r') as f:
            self.header_line = f.readline()
        super().read(filenames, encoding)

    def to_hdf_group(self, target: h5py.Group, separate_into_groups: bool = True) -> h5py.Group:
        current_track_order = h5py.get_config().track_order
        h5py.get_config().track_order = True
        for section in self.sections():
            # grpname = None
            if '----' in section:
                grpname = section.strip('----').strip()
            elif '===' in section:
                grpname = section.replace('=', '').strip()
            else:
                grpname = section
            if grpname:
                param_dict = dict(self.items(section))
                if param_dict:
                    if separate_into_groups:
                        if 'conversion' in grpname:
                            short_grpname = 'conversion'
                        elif 'pre-' in grpname:
                            short_grpname = 'preprocessing'
                        elif 'post-' in grpname:
                            short_grpname = 'postprocessing'
                        elif 'PIV processing' in grpname:
                            short_grpname = 'processing'
                        elif 'validation' in grpname:
                            short_grpname = 'validation'
                        else:
                            raise RuntimeError(f'Could not interprete section name {grpname}')
                        if grpname not in target:
                            g = target.create_group(short_grpname, track_order=True)
                        else:
                            g = target[grpname]
                    else:
                        g = target

                    if grpname == 'PIV conversion parameters':
                        length_conversion = param_dict.pop("View0_PIV_Conv_LengthConversion")
                        ds = g.create_dataset('View0_PIV_Conv_LengthConversion', data=eval(length_conversion))
                        length_conversion_units = param_dict.pop("View0_PIV_Conv_LengthConversionUnits").strip('"')
                        ds.attrs['units'] = f'px/{length_conversion_units}'
                        ds.attrs['standard_name'] = 'length_conversion'

                        pulse_delay = param_dict.pop("View0_PIV_Conv_PulseDelay")
                        ds = g.create_dataset('View0_PIV_Conv_PulseDelay', data=eval(pulse_delay))
                        ds.attrs['units'] = param_dict.pop("View0_PIV_Conv_PulseDelayUnits").strip('"')
                        ds.attrs['standard_name'] = 'pulse_delay'

                    if grpname == 'PIV processing parameters':
                        _value = param_dict.pop("View0_PIV_Eval_MultiGrid_SampleSize")
                        ds = g.create_dataset('View0_PIV_Eval_MultiGrid_SampleSize', data=eval(_value))
                        ds.attrs['units'] = 'pixel'
                        ds.attrs['standard_name'] = 'final_interrogation_window_size'

                        _value = param_dict.pop("View0_PIV_Eval_MultiGrid_SampleStep")
                        ds = g.create_dataset('View0_PIV_Eval_MultiGrid_SampleStep', data=eval(_value))
                        ds.attrs['units'] = 'pixel'
                        ds.attrs['standard_name'] = 'final_interrogation_window_overlap'

                    for item, value in param_dict.items():
                        # print(section, item, value)
                        if value:  # Add check for empty space after "=", if empty, a 0 wil be written as attribute
                            if value[0] == '"':
                                g.attrs[item] = value.strip('"')
                            else:
                                # evaluated_value = eval(value)
                                # if isinstance(evaluated_value, (list, tuple)):
                                #     ds = g.create_dataset(name=item, data=evaluated_value)
                                #     ds.attrs['units'] = 'pixel'
                                #     sn = pivview_to_standardnames_dict.get(item, None)
                                #     if sn:
                                #         ds.attrs['stanard_name'] = sn
                                # else:
                                g.attrs[item] = eval(value)
                        else:
                            g.attrs[item] = 0
        h5py.get_config().track_order = current_track_order
        return target

    def __getitem__(self, key):
        for section in self.sections():
            if key in section:
                key = section
        return super().__getitem__(key)

    def get_pulse_delay(self):
        return self['conversion parameters']['View0_PIV_Conv_PulseDelay']

    def read_from_dict(self, data_dict):
        for section_name, section in data_dict.items():
            self.add_section(section_name)
            for item_name, item_value in section.items():
                self.set(section_name, item_name, self._to_str(item_value))

    def to_dict(self):
        _dict = {}
        for section in self.sections():
            _section_dict = {}
            for item, value in self.items(section):
                if value:  # Add check for empty space after "=", if empty, a 'None' will be used
                    if value[0] == '"':
                        _section_dict[item] = value.strip('"')
                    elif value[0].isalpha():
                        # in that case it was a path without "..", that is possible in pivTECH *.cfg files ..
                        _section_dict[item] = value
                    else:
                        _section_dict[item] = eval(value)
                else:
                    _section_dict[item] = 'None'
            _dict[section] = _section_dict
        return _dict

    def to_json_dict(self):
        return json.dumps(self.to_dict())

    def to_hdf(self, target: Path, group_name: str = '/', overwrite=False) -> Path:
        """writes the config to HDF5 file or into a HDF5 group"""
        target = Path(target)
        mode = 'w'
        if target.exists() and not overwrite:
            mode = 'r+'

        with h5py.File(target, mode) as _h5:
            if group_name not in _h5:
                _h5.create_dataset(group_name)
            h5grp = _h5[group_name]
            self.to_hdf_group(h5grp)
        return target

    def load_from_hdf_group(self, hdf_group: h5py.Group):
        for k, v in hdf_group.items():
            # if 'piv' in k.lower() and 'parameters' in k.lower():
            if '----' not in k:
                section_name = f'---- {k} ----'
            else:
                section_name = k
            self[section_name] = {}
            for ak, av in hdf_group[k].attrs.items():
                self[section_name][ak] = self._to_str(av)

    def load_from_hdf(self, source: Path, group_name: str = '/'):
        """loads from hdf file. As default, root group is taken to look for seciont"""
        with h5py.File(source, 'r') as _h5:
            self.load_from_hdf_group(_h5[group_name])

    @staticmethod
    def _to_str(value):
        """Return string representation of a value"""
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, tuple):
            print('convertin tuple')
            return str(value)[1:-1].replace(' ', '')
        if isinstance(value, np.ndarray):
            return ",".join(list([str(v) for v in value]))
        return f'{value}'

    def write_to_file(self, target: Path, header_line=None) -> Path:
        """writes PIV config/parameter file"""
        if header_line is None:
            header_line = self.header_line
        with open(target, 'w') as configfile:
            configfile.write(f'{header_line}\n')
            self.write(configfile)
        return target


class PivViewConfigFile(PivViewParFile):
    section_name_dict = {"Stereo PIV configuration parameters": "[===== Stereo PIV configuration parameters =====]",
                         "Image files for view A": "[---- Image files for view A ----]",
                         "Image files for view B": "[---- Image files for view B ----]",

                         "Viewing parameters for view 'View0_'": "[---- Viewing parameters for view 'View0_' ----]",
                         "Camera Calibration data for 'View0_'": "[---- Camera Calibration data ----]",
                         "Viewing parameters for view 'View1_'": "[---- Viewing parameters for view 'View1_' ----]",
                         "Camera Calibration data for 'View1_'": "[---- Camera Calibration data ----]",
                         "Disparity correction between View0 and View1": "[---- Disparity correction between View0 and View1 ----]",

                         "PIV-Parameters for VIEW A": "[ ====== PIV-Parameters for VIEW A ======= ]",
                         "PIV Processing Parameters for 'View0_'": "[ PIV Processing Parameters ]",
                         "PIV processing parameters for 'View0_'": "[---- PIV processing parameters ----]",
                         "PIV validation parameters for 'View0_'": "[---- PIV validation parameters ----]",
                         "PIV conversion parameters for 'View0_'": "[---- PIV conversion parameters ----]",
                         "PIV image pre-processing parameters for 'View0_'": "[---- PIV image pre-processing parameters ----]",

                         "PIV-Parameters for VIEW B": "[ ====== PIV-Parameters for VIEW B ======= ]",
                         "PIV Processing Parameters for 'View1_'": "[ PIV Processing Parameters ]",
                         "PIV processing parameters for 'View1_'": "[---- PIV processing parameters ----]",
                         "PIV validation parameters for 'View1_'": "[---- PIV validation parameters ----]",
                         "PIV conversion parameters for 'View1_'": "[---- PIV conversion parameters ----]",
                         "PIV image pre-processing parameters for 'View1_'": "[---- PIV image pre-processing parameters ----]",

                         "Post-Processing Parameters": "[ ====== Post-Processing Parameters ======= ]",
                         "PIV post-processing parameters": "[---- PIV post-processing parameters ----]"
                         }

    def read(self, filenames: Path, encoding=None):
        # read in lines and store them in tmp file, which is then
        # read in. the new file is manipulated in such a way that each
        # section name is unique. The unique identifier added will
        # be removed when is written to file
        rename_dict = {}

        with open(filenames, 'r', encoding=encoding) as f:
            lines = f.readlines()

        _tmp_name = Path(next(tempfile._get_candidate_names()))
        tmp_file = Path.joinpath(Path(tempfile.gettempdir()), _tmp_name)
        with open(tmp_file, 'w') as ftmp:
            for iline, line in enumerate(lines):
                _line = line.strip()
                both_views_in_line = 'View0' in _line and 'View1' in _line
                new_section_name = None
                if '[----' in _line and '---]' in _line and ' for ' not in _line and not both_views_in_line:
                    _splt = _line.split('----')
                    # check if View0_ or View1_ is in the next 3 lines
                    if 'View0_' in lines[iline + 1] or 'View0_' in lines[iline + 2] or 'View0_' in lines[iline + 3]:
                        new_section_name = f"[{_splt[1].strip()} for 'View0_']"
                    elif 'View1_' in lines[iline + 1] or 'View1_' in lines[iline + 2] or 'View1_' in lines[iline + 3]:
                        new_section_name = f"[{_splt[1].strip()} for 'View1_']"
                    if new_section_name:
                        _line = new_section_name
                    else:
                        _line = f'[{_splt[1].strip()}]'
                elif _line == '[ PIV Processing Parameters ]':
                    if 'View0_' in lines[iline + 1] or 'View0_' in lines[iline + 2] or 'View0_' in lines[iline + 3]:
                        new_section_name = "[PIV Processing Parameters for 'View0_']"
                    elif 'View1_' in lines[iline + 1] or 'View1_' in lines[iline + 2] or 'View1_' in lines[iline + 3]:
                        new_section_name = "[PIV Processing Parameters for 'View1_']"
                    if new_section_name:
                        rename_dict[new_section_name] = _line
                        _line = new_section_name
                elif '#!PIV' in _line:
                    self.header = _line
                elif '---' in _line:
                    _line = f'[{_line[1:-1].replace("-", "").strip()}]'
                elif '===' in _line:
                    _line = f'[{_line[1:-1].replace("=", "").strip()}]'

                ftmp.write(f'{_line.strip()}\n')
        super().read(tmp_file, encoding)

    def write_to_file(self, target: Path, header_line=None) -> Path:
        """writes with wrong section names and replaces in text file afterwards"""
        super().write_to_file(target, header_line)
        with open(target, "w") as f:
            for section_name, section_pivview_name in self.section_name_dict.items():
                f.write(f'{section_pivview_name}\n')
                for item in self.items(section_name):
                    f.write(f'{item[0]} = {item[1]}\n')
        return target

    def load_from_hdf_group(self, hdf_group: h5py.Group):
        # all_section_names = list(hdf_group.items())
        # special order like PIVview uses it (when writing hdf groups track_order somehow does not work...)
        # that could have solved the issue of defining the order...
        for k in self.section_name_dict.keys():
            section_name = k
            self[section_name] = {}
            for ak, av in hdf_group[k].attrs.items():
                self[section_name][ak] = self._to_str(av)


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
                                                                          standardized_name_table=config[
                                                                              'standardized_name_table'])
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
