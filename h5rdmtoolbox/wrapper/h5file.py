import datetime
import logging
import os
import pathlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import h5py
# noinspection PyUnresolvedReferences
import pint_xarray
from h5py._hl.base import phil
from h5py._objects import ObjectID
from pint_xarray import unit_registry as ureg

# noinspection PyUnresolvedReferences
from . import xr2hdf
from .h5attr import WrapperAttributeManager
from .h5ds import H5Dataset
from .h5grp import H5Group
from .. import config
from .. import utils
from .._user import user_dirs
from .._version import __version__
from ..conventions.standard_name import StandardNameTable
from ..database import filequery

# from ..conventions.layout import H5Layout

logger = logging.getLogger(__package__)

ureg.default_format = config.UREG_FORMAT

H5File_layout_filename = Path.joinpath(user_dirs['layouts'],
                                       'H5File.hdf')


class H5File(h5py.File, H5Group):
    """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
    It enables additional features and adds new methods streamlining the work with
    HDF5 files and incorporates usage of so-called naming-conventions and layouts.
    All features from h5py packages are preserved."""

    @property
    def attrs(self) -> 'WrapperAttributeManager':
        """Return an attribute manager that is inherited from h5py's attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    @property
    def version(self) -> str:
        """Return version stored in file"""
        return self.attrs.get('__h5rdmtoolbox_version__')

    @property
    def modification_time(self) -> datetime:
        """Return creation time from file"""
        return datetime.fromtimestamp(self.hdf_filename.stat().st_mtime,
                                      tz=timezone.utc).astimezone()
        # return datetime.fromtimestamp(self.hdf_filename.stat().st_mtime,
        #                               tz=timezone.utc).astimezone().strftime(datetime_str)

    @property
    def creation_time(self) -> datetime:
        """Return creation time from file"""
        return datetime.fromtimestamp(self.hdf_filename.stat().st_ctime,
                                      tz=timezone.utc).astimezone()
        # return datetime.fromtimestamp(self.hdf_filename.stat().st_ctime,
        #                               tz=timezone.utc).astimezone().strftime(datetime_str)
        # from dateutil import parser
        # return parser.parse(self.attrs.get('creation_time'))

    @property
    def filesize(self):
        """
        Returns file size in bytes (or other units if asked)

        Returns
        -------
        _bytes
            file size in byte

        """
        _bytes = os.path.getsize(self.filename)
        return _bytes * ureg.byte

    def __init__(self, name: Path = None, mode='r', title=None, standard_name_table=None,
                 layout: Union[Path, str, 'H5Layout'] = 'H5File',
                 driver=None, libver=None, userblock_size=None,
                 swmr=False, rdcc_nslots=None, rdcc_nbytes=None, rdcc_w0=None,
                 track_order=None, fs_strategy=None, fs_persist=False, fs_threshold=1,
                 **kwds):
        _tmp_init = False
        if name is None:
            _tmp_init = True
            logger.debug("An empty H5File class is initialized")
            name = utils.touch_tmp_hdf5_file()
        elif isinstance(name, ObjectID):
            pass
        elif not isinstance(name, (str, Path)):
            raise ValueError(
                f'It seems that no proper file name is passed: type of {name} is {type(name)}')
        else:
            if mode == 'r+':
                if not Path(name).exists():
                    _tmp_init = True
                    # "touch" the file, so it exists
                    with h5py.File(name, mode='w', driver=driver,
                                   libver=libver, userblock_size=userblock_size, swmr=swmr,
                                   rdcc_nslots=rdcc_nslots, rdcc_nbytes=rdcc_nbytes, rdcc_w0=rdcc_w0,
                                   track_order=track_order, fs_strategy=fs_strategy, fs_persist=fs_persist,
                                   fs_threshold=fs_threshold,
                                   **kwds) as _h5:
                        if title is not None:
                            _h5.attrs['title'] = title

        if _tmp_init:
            mode = 'r+'
        if not isinstance(name, ObjectID):
            self.hdf_filename = Path(name)
        super().__init__(name=name, mode=mode, driver=driver,
                         libver=libver, userblock_size=userblock_size, swmr=swmr,
                         rdcc_nslots=rdcc_nslots, rdcc_nbytes=rdcc_nbytes, rdcc_w0=rdcc_w0,
                         track_order=track_order, fs_strategy=fs_strategy, fs_persist=fs_persist,
                         fs_threshold=fs_threshold,
                         **kwds)

        if not _tmp_init and self.mode == 'r' and title is not None:
            raise RuntimeError('No write intent. Cannot write title.')

        if self.mode != 'r':
            # update file toolbox version, wrapper version
            self.attrs['__h5rdmtoolbox_version__'] = __version__
            self.attrs['__wrcls__'] = self.__class__.__name__

            # set title and layout
            if title is not None:
                self.attrs['title'] = title

        if standard_name_table is not None:
            if isinstance(standard_name_table, str):
                standard_name_table = StandardNameTable.load_registered(standard_name_table)
            if self.standard_name_table != standard_name_table:
                self.standard_name_table = standard_name_table
        self.layout = layout

    def check(self, grp: Union[str, h5py.Group] = '/') -> int:
        """Run layout check. This method may be overwritten to add conditional
         checking.

         Parameters
         ----------
         grp: str or h5py.Group, default='/'
            Group from where to start the layout check.
            Per default starts at root level

         Returns
         -------
         int
            Number of detected issues.
         """
        return self.layout.check(self[grp])

    def moveto(self, destination: Path, overwrite: bool = False) -> Path:
        """Move the opened file to a new destination.

        Parameters
        ----------
        destination : Path
            New filename.
        overwrite : bool
            Whether to overwrite an existing file.

        Return
        ------
        new_filepath : Path
            Path to new file locationRaises

        Raises
        ------
        FileExistsError
            If destination file exists and overwrite is False.
        """
        dest_fname = Path(destination)
        if dest_fname.exists() and not overwrite:
            raise FileExistsError(f'The target file "{dest_fname}" already exists and overwriting is set to False.'
                                  ' Not moving the file!')
        logger.debug(f'Moving file {self.hdf_filename} to {dest_fname}')

        if not dest_fname.parent.exists():
            Path.mkdir(dest_fname.parent, parents=True)
            logger.debug(f'Created directory {dest_fname.parent}')

        mode = self.mode
        self.close()
        shutil.move(self.hdf_filename, dest_fname)
        super().__init__(dest_fname, mode=mode)
        new_filepath = dest_fname.absolute()
        self.hdf_filename = new_filepath
        return new_filepath

    def saveas(self, filename: Path, overwrite: bool = False) -> "H5File":
        """
        Save this file under a new name (effectively a copy). This file is closed and re-opened
        from the new destination usng the previous file mode.

        Parameters
        ----------
        filename: Path
            New filename.
        overwrite: bool, default=False
            Whether to not to overwrite an existing filename.

        Returns
        -------
        H5File
            Instance of moved H5File

        """
        _filename = Path(filename)
        if _filename.is_file():
            if overwrite:
                os.remove(_filename)
            else:
                raise FileExistsError("Note: File was not moved to new location as a file already exists with this name"
                                      " and overwriting was disabled")

        src = self.filename
        mode = self.mode
        self.close()  # close this instance

        shutil.copy2(src, _filename)
        self.hdf_filename = _filename
        return H5File(_filename, mode=mode)

    def reopen(self, mode: str = 'r+') -> None:
        """Open the closed file"""
        self.__init__(self.hdf_filename, mode=mode)

    @staticmethod
    def open(filename: Union[str, pathlib.Path], mode: str = "r+") -> 'H5File':
        """Open the closed file and use the correct wrapper class

        Parameters
        ----------
        mode: str
            Mode used to open the file: r, r+, w, w-, x, a

        Returns
        -------
        Subclass of H5File
        """
        return H5File(filename, mode)


class H5Files(filequery.Files):
    def __enter__(self):
        for filename in self._list_of_filenames:
            try:
                h5file = H5File(filename, mode='r')
                self._opened_files[str(filename)] = h5file
            except RuntimeError as e:
                print(f'RuntimeError: {e}')
                for h5file in self._opened_files.values():
                    h5file.close()
                self._opened_files = {}
        return self


H5Dataset._h5grp = H5Group
H5Dataset._h5ds = H5Dataset

H5Group._h5grp = H5Group
H5Group._h5ds = H5Dataset

# noinspection PyUnresolvedReferences
from ..conventions import standard_name, units, title, software, long_name, data
