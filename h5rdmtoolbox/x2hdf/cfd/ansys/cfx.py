import logging
import os
import pathlib
from typing import List, Dict, Union

import dotenv
import numpy as np
import pandas as pd
import xarray as xr

from . import session, PATHLIKE, ccl, CFX_DOTENV_FILENAME, mon
from .utils import change_suffix

logger = logging.getLogger(__package__)
dotenv.load_dotenv(CFX_DOTENV_FILENAME)

CFX5SOLVE = os.environ.get("cfx5solve")
AUXDIRNAME = '.x2hdf'


class CFXFilename:
    suffix = ''
    __slots__ = ('filename',)

    def __init__(self, filename):
        self.filename = pathlib.Path(filename)
        if self.filename.suffix == self.suffix:
            raise ValueError(f'Wrong suffix for a {self.__class__.__name__} filename: {self.filename.suffix} != .cfx')


class CFXCaseFilename:
    suffix = '.cfx'


class CFXResFilename:
    suffix = '.res'

    @property
    def number(self):
        return int(self.filename.stem.rsplit('_')[1])


class CFXOUTFile(CFXResFilename):
    suffix = '.out'


class MonitorObject:

    def __init__(self, expression_value: str, coord_frame: str = 'Coord 0'):
        """
        TODO: expression and coord frame could also be objects
        """
        self.coord_frame = coord_frame
        self.expression_value = expression_value


class MonitorUserPoint(xr.DataArray):
    __slots__ = ()


class MonitorUserExpression(xr.DataArray):
    __slots__ = ()


def process_monitor_string(monitor_str: str):
    if monitor_str not in ('COMMAND FILE', 'monitor', 'LIBRARY', 'FLOW: Flow Analysis 1'):
        _split = monitor_str.split(',')
        _groups = _split[0:-1]
        groups = _groups.copy()
        coords = {}
        for igrp, grp in enumerate(_groups):
            if "x=" in grp:
                coords['x'] = float(grp.split('=')[1].strip('"'))
                groups.pop(igrp)
            elif "y=" in grp:
                coords['y'] = float(grp.split('=')[1].strip('"'))
                groups.pop(igrp - len(coords) + 1)
            elif "z=" in grp:
                coords['z'] = float(grp.split('=')[1].strip('"'))
                groups.pop(igrp - len(coords) + 1)

        group = '/'.join(groups)
        name, _units = _split[-1].split(' [')
        if _units == ']':
            _units = ''
        return {'group': group, 'name': name, 'units': _units[:-1], 'coords': coords}


def _str_to_UserPoint(input_str: str, data: np.ndarray) -> Union[MonitorUserPoint, MonitorUserExpression]:
    """extracts info from a user point string and returns a MonitorUserPoint class"""
    monitor_pt_str_dict = process_monitor_string(input_str)
    coords = monitor_pt_str_dict.pop('coords')
    if len(coords) == 0:
        coords = None
    return MonitorUserPoint(data=data,
                            dims=('iteration',),
                            attrs=monitor_pt_str_dict,
                            coords=coords)


class MonitorDataFrame(pd.DataFrame):

    @property
    def user_points(self) -> Dict:
        user_point_list = [_str_to_UserPoint(n, self[n]) for n in self.columns if n.find('USER POINT') == 0]
        return {up.attrs['name']: up for up in user_point_list if up is not None}


class CFXFile:
    """Base wrapper class around a generic Ansys CFX file"""

    def __init__(self, filename: CFXCaseFilename):
        self.filename = pathlib.Path(filename).resolve()
        self.working_dir = self.filename.parent.resolve()

        if self.filename.suffix == '.res':
            self.aux_dir = self.working_dir.joinpath(AUXDIRNAME)
        else:
            self.aux_dir = self.working_dir.joinpath(AUXDIRNAME)
        if not self.aux_dir.exists():
            self.aux_dir.mkdir(parents=True)


class MonitorData(CFXFile):

    def __init__(self, filename):
        super(MonitorData, self).__init__(filename)
        monitor_filename = f'{self.filename.stem}.monitor'
        self.cfx_filename = filename
        self.filename = self.aux_dir.joinpath(monitor_filename)
        self._data = pd.DataFrame()

    def __getitem__(self, item):
        return self._data[item]

    @property
    def is_out_of_date(self):
        if self.filename.exists():
            return self.filename.stat().st_mtime < self.cfx_filename.stat().st_mtime
        return True

    @property
    def names(self):
        return self.data.columns

    def _write_file(self) -> None:
        self.filename = mon.get_monitor_data_by_category(self.cfx_filename, out=self.filename)

    def _read_data(self) -> None:
        if not self.filename.exists() or self.is_out_of_date:
            self._write_file()
        self._data = pd.read_csv(self.filename)

    @property
    def data(self) -> MonitorDataFrame:
        if not self.filename.exists():
            self._write_file()
            self._data = pd.read_csv(self.filename)
            return self._data
        else:
            if self._data.size == 0:
                self._read_data()
            return MonitorDataFrame(self._data)

    @property
    def user_points(self):
        return self.data.user_points


class OutFile(MonitorData):

    def __init__(self, filename, res_filename):
        super().__init__(filename)
        filename = f'{self.filename.stem}.outdata'
        self.filename = self.aux_dir.joinpath(filename)
        self.res_filename = res_filename
        self.out_filename = change_suffix(res_filename, '.out')
        self._data = pd.DataFrame()

    def _write_file(self) -> None:
        self._data = mon.extract_out_data(self.out_filename)
        self._data.to_csv(self.filename)

    def get_mesh_info(self) -> pd.DataFrame:
        if self.filename.exists():
            return mon.mesh_info_from_file(self.filename)
        return pd.DataFrame()

    def _read(self):
        if not self.filename.exists():
            self._write_file()

    @property
    def data(self):
        return self._data


class CFXResFile(CFXFile):
    """Class wrapped around the *.res case file"""

    def __init__(self, filename, def_filename):
        super(CFXResFile, self).__init__(filename)
        self.case_stem = self.filename.stem.rsplit('_', 1)[0]
        self.def_filename = def_filename

    @property
    def monitor(self):
        return MonitorData(self.filename)

    @property
    def out_data(self):
        return OutFile(self.filename, self.filename)


class CFXResFiles:

    def __init__(self, filenames: List[PATHLIKE], def_filename: PATHLIKE, sort: bool = True):
        self.filenames = filenames
        self.def_filename = def_filename
        self.sort = sort
        self.update()

    def update(self):
        if self.sort:
            self.cfx_res_files = [CFXResFile(filename, self.def_filename) for filename in sorted(self.filenames)]
        else:
            self.cfx_res_files = [CFXResFile(filename, self.def_filename) for filename in self.filenames]

    @property
    def latest(self):
        self.update()
        if len(self.cfx_res_files) > 0:
            return self.cfx_res_files[-1]
        else:
            return None


class CFXCase(CFXFile):
    """Class wrapped around the *.cfx case file.

    Case assumtions:
    ----------------
    The case file (.cfx) and the definition file ('.def') have the same stem, e.g.:
    `mycase.cfx` and `mycase.def`.
    The result files (.res) will look like `mycase_001.res` and `maycase_002.res` and so on.
    """

    def __init__(self, filename):
        """
        Avoids error when multiple cfx files are available in
        one folder, e.g. *._frz, *_trn.cfx
        """
        super().__init__(filename)
        if not self.filename.exists():
            raise FileExistsError(f'CFX file does not exist: {self.filename}')
        self.refresh()

    @property
    def name(self):
        return self.filename.stem

    @property
    def latest(self, refresh=False):
        """Returns the latest .cfx file"""
        return self.res_files.latest

    def refresh(self):
        """Mainly scans for all relevant case files and updates content if needed"""
        if not self.filename.suffix == '.cfx':
            raise ValueError(f'Expected suffix .cfx and not {self.filename.suffix}')
        self.working_dir = self.filename.parent
        if not self.working_dir.exists():
            raise NotADirectoryError('The working directory does not exist. Can only work with existing cases!')

        def_filename = change_suffix(self.filename, '.def')
        if not def_filename.exists():
            print('creating def file from cfx')
            def_filename = session.cfx2def(self.filename)
            if not def_filename.exists():
                raise RuntimeError(f'Seems that solver file was not written from {self.filename}')

        res_filename_list = list(self.working_dir.glob(f'{self.filename.stem}*.res'))
        self.res_files = CFXResFiles(filenames=res_filename_list, def_filename=def_filename)
        ccl_filename = ccl.generate(self.filename)
        self.ccl_filename = ccl_filename
