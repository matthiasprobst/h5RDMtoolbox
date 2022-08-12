import logging
import os
import pathlib
import time
from typing import List, Dict, Union

import dotenv
import h5py
import pandas as pd
import xarray as xr
from numpy.typing import ArrayLike
from ....conventions.translations import cfx_to_standard_name

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


def _str_to_UserPoint(input_str: str, data: ArrayLike) -> Union[MonitorUserPoint, MonitorUserExpression]:
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
        if not self.filename.exists():
            raise FileExistsError(f'File does not exist: {self.filename}')

        self.working_dir = self.filename.parent.resolve()
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
    """Ansys CFX Result class"""

    def __init__(self, filenames: List[PATHLIKE], def_filename: PATHLIKE, sort: bool = True):
        self.filenames = filenames
        self.def_filename = def_filename
        self.sort = sort
        self.cfx_res_files = []
        self.update()

    def __len__(self):
        return len(self.cfx_res_files)

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

        if not self.filename.suffix == '.cfx':
            raise ValueError(f'Expecting file suffix .cfx, not {self.filename.suffix}')

        def_filename = change_suffix(self.filename, '.def')
        if not def_filename.exists():
            self.def_filename = None
        else:
            self.def_filename = def_filename

        res_filename_list = list(self.working_dir.glob(f'{self.filename.stem}*.res'))
        self.res_files = CFXResFiles(filenames=res_filename_list, def_filename=self.def_filename)

    def __repr__(self):
        return f'CFX Case <{self.filename.name}> with {len(self.res_files)} result file(s)'

    def __str__(self):
        return self.__repr__()

    @property
    def has_result_files(self) -> bool:
        return len(self.res_files) > 0

    @property
    def has_def_file(self) -> bool:
        if self.def_filename is None:
            return False
        return self.def_filename.exists()

    @property
    def hdf(self):
        class HDFFileInterface:
            def __init__(self, filename, cfx_case):
                self._filename = pathlib.Path(filename)
                self._cfx_case = cfx_case

            def exists(self):
                return self._filename.exists()

            @property
            def filename(self):
                return self._filename

            @property
            def out_of_date(self) -> bool:
                """is younger than res if exists. if no result files exist, if is younger than cfx"""
                if len(self._cfx_case.res_files) == 0:
                    cmp_mtime = self._cfx_case.filename.stat().st_mtime
                else:
                    cmp_mtime = self._cfx_case.latest.filename.stat().st_mtime
                if not self._filename.exists():
                    return True
                this_mtime = self._filename.stat().st_mtime
                return this_mtime < cmp_mtime

            def unlink(self):
                self._filename.unlink(missing_ok=True)

            def generate(self, force: bool = False, verbose: bool = True):
                if self.out_of_date or force:
                    st = time.perf_counter()
                    ccl_filename = ccl.generate(self._cfx_case.filename, verbose=verbose)
                    elapsed_time = time.perf_counter() - st
                    if verbose:
                        print(f'Conversion tool {elapsed_time} s')
                    ccl.CCLTextFile(ccl_filename).to_hdf(self._filename)

                    if len(self._cfx_case) == 0:
                        monitor_data = None
                    else:
                        monitor_data = self._cfx_case.latest.monitor.data

                    scale_sub_names = ('ACCUMULATED TIMESTEP', 'CURRENT TIMESTEP', 'TIME',)
                    scale_monitor_names = []
                    scale_datasets = []
                    with h5py.File(self._filename, 'r+') as h5:
                        if monitor_data is not None:
                            for k in monitor_data.keys():
                                if any([scale_name in k for scale_name in scale_sub_names]):
                                    scale_monitor_names.append(k)
                                    meta_dict = process_monitor_string(k)
                                    ds_name = f'{meta_dict["group"]}/{meta_dict["name"]}'
                                    ds = h5.create_dataset(name=ds_name, data=monitor_data[k])
                                    ds.attrs['units'] = meta_dict['units']
                                    try:
                                        ds.attrs['standard_name'] = cfx_to_standard_name[meta_dict["name"].lower()]
                                    except KeyError:
                                        logger.debug(f'Could not set standard name for {ds_name}')
                                    ds.make_scale()
                                    scale_datasets.append(ds)

                            grp = h5.create_group('monitor')
                            for k, v in monitor_data.items():
                                if k not in scale_monitor_names:
                                    meta_dict = process_monitor_string(k)
                                    ds = grp.create_dataset(name=f'{meta_dict["group"]}/{meta_dict["name"]}', data=v)
                                    try:
                                        ds.attrs['standard_name'] = cfx_to_standard_name[meta_dict["name"].lower()]
                                    except KeyError:
                                        logger.debug(f'Could not set standard name for {ds_name}. Using name '
                                                     f'as long_name instead')
                                        ds.attrs['long_name'] = meta_dict['name']
                                    ds.attrs['units'] = meta_dict['units']
                                    ds.dims[0].attach_scale(h5['ACCUMULATED TIMESTEP'])
                                    for scale_dataset in scale_datasets:
                                        ds.dims[0].attach_scale(scale_dataset)
                                    if meta_dict['coords']:
                                        ds.attrs['COORDINATES'] = list(meta_dict['coords'].keys())
                                        for kc, vc in meta_dict['coords'].items():
                                            dsc = grp[meta_dict["group"]].create_dataset(kc, data=vc)

                                            try:
                                                ds.attrs['standard_name'] = cfx_to_standard_name[kc]
                                            except KeyError:
                                                logger.debug(f'Could not set standard name for {ds_name}. Using name '
                                                             f'as long_name instead')
                                                ds.attrs['long_name'] = kc
                                            # NOTE: ASSUMING [m] is the default units but TODO check in CCL file what the base unit is!
                                            dsc.attrs['units'] = 'm'

        return HDFFileInterface(change_suffix(self.filename, '.hdf'), self)

    def write_def(self, def_filename=None, overwrite=True):
        if def_filename is None:
            def_filename = self.def_filename
        else:
            def_filename = pathlib.Path(def_filename)

        if not overwrite:
            if def_filename.exists():
                raise FileExistsError(f'Not creating def file as it exists and overwrite is False')

        def_filename = session.cfx2def(self.filename)
        self.def_filename = def_filename
        return def_filename

    def __len__(self):
        return len(self.res_files)

    @property
    def name(self):
        return self.filename.stem

    @property
    def latest(self, refresh=False):
        """Returns the latest .cfx file"""
        return self.res_files.latest

    # def refresh(self):
    #     """Mainly scans for all relevant case files and updates content if needed"""
    #     if not self.filename.suffix == '.cfx':
    #         raise ValueError(f'Expected suffix .cfx and not {self.filename.suffix}')
    #     self.working_dir = self.filename.parent
    #     if not self.working_dir.exists():
    #         raise NotADirectoryError('The working directory does not exist. Can only work with existing cases!')
    #
    #
    #     res_filename_list = list(self.working_dir.glob(f'{self.filename.stem}*.res'))
    #     self.res_files = CFXResFiles(filenames=res_filename_list, def_filename=def_filename)
    #     ccl_filename = ccl.generate(self.filename)
    #     self.ccl_filename = ccl_filename
