import h5py
import pathlib
from typing import Union, Generator, List

from .groupdb import GroupDB
from .nonsearchable import NonInsertableDatabaseInterface
from .. import lazy
from ..interface import HDF5DatabaseInterface


class FileDB(NonInsertableDatabaseInterface, HDF5DatabaseInterface):
    """A database interface for an HDF5 file, where the filename is given."""

    def __init__(self, filename: Union[str, pathlib.Path]):
        self.filename = pathlib.Path(filename)

    def find_one(self, *args, **kwargs) -> lazy.LHDFObject:
        """Please refer to the docstring of the find_one method of the GroupDB class"""
        with h5py.File(self.filename, 'r') as h5:
            return GroupDB(h5).find_one(*args, **kwargs)

    def find(self, *args, **kwargs) -> Generator[lazy.LHDFObject, None, None]:
        """Please refer to the docstring of the find method of the GroupDB class"""
        with h5py.File(self.filename, 'r') as h5:
            results = list(GroupDB(h5).find(*args, **kwargs))
        for r in results:
            yield r


class FilesDB(NonInsertableDatabaseInterface, HDF5DatabaseInterface):
    """A database interface for an HDF5 file, where the filename is given."""

    def __init__(self, filenames: List[Union[str, pathlib.Path]]):
        self.filenames = list(set(pathlib.Path(filename) for filename in filenames))

    @classmethod
    def from_folder(cls,
                    folder: Union[str, pathlib.Path],
                    hdf_suffixes: Union[str, List[str]] = '.hdf',
                    recursive: bool = False):
        """Create a FilesDB from a folder containing HDF5 files"""
        if isinstance(hdf_suffixes, str):
            hdf_suffixes = [hdf_suffixes]

        folder = pathlib.Path(folder)
        filenames = []

        for suffix in hdf_suffixes:
            if recursive:
                filenames.extend(folder.rglob(f'*{suffix}'))
            else:
                filenames.extend(folder.glob(f'*{suffix}'))
        return cls(filenames)

    def insert_filename(self, filename: Union[str, pathlib.Path]):
        """Insert a filename to the database"""
        self.filenames.append(pathlib.Path(filename))
        self.filenames = list(set(self.filenames))

    def find_one(self, *args, **kwargs) -> lazy.LHDFObject:
        """Call find_one on all the files registerd. If more than one file
        contains the object, the first one is returned. If you want to find one per file,
        call find_one_per_file instead."""
        for filename in self.filenames:
            with h5py.File(filename, 'r') as h5:
                ret = GroupDB(h5).find_one(*args, **kwargs)
                if ret:
                    return ret
        return

    def find(self, *args, **kwargs) -> Generator[lazy.LHDFObject, None, None]:
        all_results = []
        for filename in self.filenames:
            with h5py.File(filename, 'r') as h5:
                ret = GroupDB(h5).find(*args, **kwargs)
                all_results.extend(ret)
        return all_results
