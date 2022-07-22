import json
import subprocess
import tempfile
from configparser import ConfigParser
from os import environ
from pathlib import Path

import h5py
import numpy as np
from netCDF4 import Dataset as ncDataset

from ...utils import _make_bold

try:
    NCDF2PAR = Path(environ.get('ncdf2par'))
except TypeError:
    NCDF2PAR = None


def _is_nc_file(nc_filename: Path):
    """tries to open a nc file and returns success"""
    try:
        with ncDataset(nc_filename, 'r') as nc_rootgrp:
            _ = nc_rootgrp.dimensions
            return True
    except OSError:
        return False


def read_header_line(filenames: Path) -> str:
    with open(filenames, 'r') as f:
        return f.readline()


class PivViewParFile(ConfigParser):
    filename: Path = None
    header_line: str = ''
    header: str or None = None

    optionxform = str  # otherwise makes items lowercase

    def __str__(self):
        out_str = ''
        for k in self.sections():
            out_str += _make_bold(f'\n{k.strip(" ").strip("-").strip()}')
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
        self.header_line = read_header_line(filenames)
        super().read(filenames, encoding)

    def to_hdf_group(self, target: h5py.Group) -> h5py.Group:
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
                if grpname not in target:
                    g = target.create_group(grpname, track_order=True)
                else:
                    g = target[grpname]
                for item, value in self.items(section):
                    # print(section, item, value)
                    if value:  # Add check for empty space after "=", if empty, a 0 wil be written as attribute
                        if value[0] == '"':
                            g.attrs[item] = value.strip('"')
                        else:
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
        """returns string representation of a value"""
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
