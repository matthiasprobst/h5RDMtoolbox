import h5py
import pathlib
from typing import Union, Dict

from . import lazy
from .filequery import Files
from .._logger import loggers

logger = loggers['database']


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


class FileDB:
    """File as a database"""

    def __init__(self, filename: pathlib.Path):
        filename = pathlib.Path(filename)
        if not filename.is_file():
            raise ValueError(f'{filename} is not a file')
        self.filename = filename

    def find(self, flt: Union[Dict, str],
             objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
             rec: bool = True,
             ignore_attribute_error: bool = False):
        """Find"""
        from .. import File
        with File(self.filename) as h5:
            return [lazy.lazy(r) for r in h5.find(flt, objfilter, rec, ignore_attribute_error)]

    def find_one(self,
                 flt: Union[Dict, str],
                 objfilter=None,
                 rec: bool = True,
                 ignore_attribute_error: bool = False):
        """Find one occurrence"""
        from .. import File
        with File(self.filename) as h5:
            return lazy.lazy(h5.find_one(flt, objfilter, rec, ignore_attribute_error))


class FolderDB:
    """Folder with HDF5 files as a database

    Parameters
    ----------
    folder : pathlib.Path
        folder with HDF5 files
    pattern : str, optional
        pattern to search for, by default '*.hdf'
    rec : bool, optional
        search recursively for hdf files within the given folder, by default True
    """

    def __init__(self, folder: pathlib.Path, pattern='*.hdf', rec: bool = True):
        folder = pathlib.Path(folder)
        if not folder.is_dir():
            raise ValueError(f'{folder} is not a directory')
        self.folder = folder
        if rec:
            self.filenames = self.folder.rglob(pattern)
        else:
            self.filenames = self.folder.glob(pattern)

    def find(self,
             flt: Union[Dict, str],
             objfilter=None, rec: bool = True,
             ignore_attribute_error: bool = False):
        """Find"""
        from .. import File
        with Files(self.filenames, file_instance=File) as h5:
            return [lazy.lazy(r) for r in h5.find(flt, objfilter, rec, ignore_attribute_error)]

    def find_one(self,
                 flt: Union[Dict, str],
                 objfilter=None,
                 rec: bool = True,
                 ignore_attribute_error: bool = False):
        """Find one occurrence"""
        from .. import File
        with Files(self.filenames, file_instance=File) as h5:
            return lazy.lazy(h5.find_one(flt, objfilter, rec, ignore_attribute_error))


__all__ = ['logger', 'set_loglevel', 'Files']
