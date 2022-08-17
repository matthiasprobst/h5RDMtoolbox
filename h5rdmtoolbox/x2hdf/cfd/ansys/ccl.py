import logging
import os
import pathlib
import shutil
from dataclasses import dataclass
from typing import Union

import dotenv
import h5py
import numpy as np

from . import session, AnsysInstallation, PATHLIKE, CFX_DOTENV_FILENAME
from .cmd import call_cmd
from .session import cfx2def
from .utils import change_suffix

dotenv.load_dotenv(CFX_DOTENV_FILENAME)

logger = logging.getLogger('cfdtoolkit')


@dataclass
class CCLDataField:
    filename: PATHLIKE
    line: int
    name: str
    value: str

    def set(self, new_value) -> None:
        """updates the value in the CCL file"""
        if not self.value == new_value:
            self.value = new_value
            bak_filename = shutil.copy(self.filename, f'{self.filename}.bak')
            shutil.copy(self.filename, bak_filename)
            with open(self.filename, 'r') as f:
                lines = f.readlines()
                target_line = lines[self.line]
            intendation_count = target_line.split(self.name)[0]
            lines[self.line] = f'{intendation_count}{self.name} = {new_value}\n'
            with open(self.filename, 'w') as f:
                f.writelines(lines)


class CCLGroup:

    def __init__(self, filename, grp_line, end_line, indentation_length,
                 intendation_step, all_lines,
                 all_indentation, name=None, verbose=False):
        self.filename = filename

        self.all_lines = all_lines
        self.all_indentation = all_indentation

        self.grp_line = grp_line
        if end_line == -1:
            self.end_line = len(self.all_lines)
        else:
            self.end_line = end_line

        self.group_type = None
        if name is None:
            _name = self.all_lines[self.grp_line].strip()
            if _name.endswith(':'):
                self.name = _name[:-1]
            else:
                self.name = _name
            self.group_type = self.name.split(':', 1)[0]
        else:
            self.name = name

        self.indentation_length = indentation_length
        self.intendation_step = intendation_step
        self.verbose = verbose

        self.sub_groups = {}
        self.find_subgroup()

    def __repr__(self):
        return self.name

    def __getitem__(self, item):
        return self.sub_groups[item]

    def keys(self):
        return self.sub_groups.keys()

    def get_lines(self):
        grp_lines = self.all_lines[self.grp_line + 1:self.end_line]
        return grp_lines

    def _lines_to_data(self, lines):
        data = {}
        for iline, line in enumerate(lines):
            linedata = line.strip().split('=')
            if len(linedata) > 1:
                name = linedata[0].strip()
                value = linedata[1].strip()
                data[linedata[0].strip()] = CCLDataField(self.filename, self.grp_line + 1 + iline, name, value)
            else:
                # all options are at top of a group. once there is a line without "=" the next group begins...
                return data
        return data

    @property
    def data(self):
        return self._lines_to_data(self.get_lines())

    def find_subgroup(self):
        if self.verbose:
            logger.debug(f'searching at indentation level '
                         f'{self.indentation_length} within '
                         f'{self.grp_line + 1} and {self.end_line}')

        found = []
        for i in self.all_indentation:
            if self.grp_line <= i[0] < self.end_line:
                if i[1] == self.indentation_length:
                    # append line number indent and
                    found.append((i[0], i[1] - 1))
                    # print(i)
        afound = np.asarray([f[0] for f in found])
        if len(afound) > 1:
            for (a, b) in zip(found[0:], found[1:]):
                if a[0] + 1 != b[0]:  # it's a group!
                    _ccl_grp = CCLGroup(self.filename, a[0], b[0],
                                        indentation_length=self.indentation_length + self.intendation_step,
                                        intendation_step=2, all_lines=self.all_lines,
                                        all_indentation=self.all_indentation)
                    self.sub_groups[_ccl_grp.name] = _ccl_grp

    def create_h5_group(self, h5grp, root_group=False, overwrite=False):
        # if skip_root=True the root group is written '/' rather
        # than to what the group name is

        if root_group:
            g = h5grp
        else:
            if self.name in h5grp:
                if overwrite:
                    del h5grp[self.name]
                else:
                    raise ValueError('Group already exists and overwrite is set to False!')
            # logger.debug(f'Creating group with name {self.name} at level: {h5grp.name}')
            g = h5grp.create_group(self.name)

        grp_lines = self.get_lines()

        grp_ind_spaces = ' ' * self.indentation_length

        # is set to false if first line in group is not an attribute of this group (no line with "=")
        grp_values_flag = True
        for line in grp_lines:
            if line[0:self.indentation_length] == grp_ind_spaces:
                if grp_values_flag:
                    try:
                        name, value = line.split('=')
                        g.attrs[name.strip()] = value.strip()
                    except:
                        grp_values_flag = False

        for name, subg in self.sub_groups.items():
            # logger.debug(name)
            subg.create_h5_group(g, overwrite=overwrite)


INTENDATION_STEP = 2


class CCLTextFile:
    """
    Reads in a ANSYS CFX *.ccl file (plain text)

    Example
    -------
    c = CCL_File(ccl_filename)
    c.write_to_hdf('ccltest.hdf', overwrite=True)
    """

    def __init__(self, filename: PATHLIKE, verbose: bool = False):
        self.filename = pathlib.Path(filename)
        self.lines = self._remove_linebreaks()
        self.indentation = self._get_indentation()
        self.intendation_step = INTENDATION_STEP
        self.root_group = CCLGroup(self.filename, 0, -1, indentation_length=self.indentation[0][1],
                                   intendation_step=self.intendation_step,
                                   all_lines=self.lines,
                                   all_indentation=self.indentation, name='root', verbose=verbose)
        self.mtime = self.filename.stat().st_mtime

    def get_flow_group(self):
        for grp in self.root_group.sub_groups.values():
            if grp.group_type == 'FLOW':
                return grp

    def to_hdf(self, hdf_filename: Union[PATHLIKE, None] = None, overwrite=True):
        if hdf_filename is None:
            hdf_filename = change_suffix(self.filename, '.hdf')
        else:
            hdf_filename = pathlib.Path(hdf_filename)

        if hdf_filename.is_file() and not overwrite:
            raise FileExistsError(f'Target HDF file exists and overwrite is set to False!')

        with h5py.File(hdf_filename, 'w') as h5:
            self.root_group.create_h5_group(h5['/'], root_group=True, overwrite=True)

        return hdf_filename

    def _remove_linebreaks(self):
        with open(self.filename, 'r') as f:
            lines = f.readlines()
        single_lines = []

        append_line = False
        for line in lines:
            _line = line.strip('\n')
            if _line != '':
                if _line[0] != '#':
                    if append_line:
                        if _line[-1] == '\\':
                            single_lines[-1] += _line[:-1]
                        else:
                            append_line = False
                            single_lines[-1] += _line.strip()
                    else:
                        if _line[-1] == '\\':
                            if append_line:
                                single_lines[-1] += _line[:-1]
                            else:
                                single_lines.append(_line[:-1])
                            append_line = True
                        else:
                            append_line = False
                            single_lines.append(_line)
        return single_lines

    def _get_indentation(self):
        indentation = []
        for i, line in enumerate(self.lines):
            l0 = len(line)
            l1 = len(line.strip(' '))
            indentation.append((i, l0 - l1))
        return indentation


def _list_of_instances_by_keyword_substring(filename, root_group, substring, class_):
    instances = []
    with h5py.File(filename) as h5:
        for k in h5[root_group].keys():
            if substring in k:
                if root_group == '/':
                    instances.append(class_(k, filename))
                else:
                    instances.append(class_(f'{root_group}/{k}', filename))
    return instances


def generate(input_file: PATHLIKE, ccl_filename: Union[PATHLIKE, None] = None,
             cfx5pre: pathlib.Path = None, overwrite: bool = True) -> pathlib.Path:
    """
    Converts a .res, .cfx or .def file into a ccl file.
    If no `ccl_filename` is provided the input filename is
    taken and extension is changed accordingly to *.ccl

    Parameters
    ----------
    input_file : PATHLIKE
        *.res or *.cfx file
    ccl_filename: PATHLIKE or None
        Where to write ccl file. Default changes extension of input to "ccl"
    cfx5pre: `Path`
        Path to exe. Default takes path from config
    overwrite: bool
        Whether to overwrite an existing ccl file

    Returns
    -------
    ccl_filename : `Path`
        Path to generated ccl file
    """
    input_file = pathlib.Path(input_file).resolve()

    if input_file.suffix not in ('.cfx', '.res', '.def'):
        raise ValueError('Please provide a ANSYS CFX file.')

    if ccl_filename is None:
        ccl_filename = change_suffix(input_file, '.ccl')
    # logger.debug(f'*.ccl input_file: {ccl_filename}')

    if input_file.suffix in ('.cfx', '.res'):
        # build def file and then call _generate_from_def
        # this is the safe way!
        if cfx5pre is None:
            cfx5pre = AnsysInstallation.cfx5pre

        def_filename = cfx2def(input_file)
        return _generate_from_def(def_filename, ccl_filename, overwrite)
    return _generate_from_def(input_file, ccl_filename, overwrite)


def _generate_from_res_or_cfx(res_cfx_filename: PATHLIKE,
                              ccl_filename: pathlib.Path, cfx5pre: str, overwrite=True) -> pathlib.Path:
    if overwrite and ccl_filename.exists():
        ccl_filename.unlink()
    if res_cfx_filename.suffix == '.cfx':
        session_filename = os.path.join(session.SESSIONS_DIR, 'cfx2ccl.pre')
    else:
        raise ValueError(f'Could not determine "session_filename"')

    random_fpath = session.copy_session_file_to_tmp(session_filename)
    _upper_ext = res_cfx_filename.suffix[1:].upper()
    session.replace_in_file(random_fpath, f'__{_upper_ext}_FILE__', res_cfx_filename)
    session.replace_in_file(random_fpath, '__CCL_FILE__', ccl_filename)

    logger.debug(f'Playing CFX session file: {random_fpath}')
    session.play_session(random_fpath, cfx5pre)
    os.remove(random_fpath)
    return ccl_filename


def _generate_from_def(def_filename: PATHLIKE,
                       ccl_filename: PATHLIKE,
                       overwrite: bool = True) -> pathlib.Path:
    """generates a ccl file from a def file"""
    if ccl_filename.exists() and overwrite:
        ccl_filename.unlink()
    cmd = f'"{AnsysInstallation.cfx5cmds}" -read -def "{def_filename}" -text "{ccl_filename}"'
    call_cmd(cmd, wait=True)

    if not ccl_filename.exists():
        raise RuntimeError(f'Failed running bash script "{cmd}"')
    return ccl_filename
