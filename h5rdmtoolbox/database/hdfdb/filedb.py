import pathlib
from typing import Union, Generator, List, Optional

import h5py

from .objdb import ObjDB
from ..interface import HDF5DBInterface
from .. import lazy


class FileDB(HDF5DBInterface):
    """A database interface for a single HDF5 file"""

    def __init__(self, filename: Union[str, pathlib.Path]):
        self.filename: str = str(filename)
        self.find = self._instance_find  # allow `find` to be a static method and instance method
        self.find_one = self._instance_find_one  # allow `find_one` to be a static method and instance method
        self.rdf_find = self._instance_rdf_find

    @staticmethod
    def find_one(filename: Union[str, pathlib.Path], *args, **kwargs) -> lazy.LazyObject:
        """Please refer to the docstring of the find_one method of the ObjDB class"""
        with h5py.File(str(filename), 'r') as h5:
            return ObjDB(h5).find_one(*args, **kwargs)

    def _instance_find(self, *args, **kwargs):
        with h5py.File(self.filename, 'r') as h5:
            return list(ObjDB(h5).find(*args, **kwargs))

    def _instance_rdf_find(self, *,
                           rdf_subject: Optional[str] = None,
                           rdf_type: Optional[str] = None,
                           rdf_predicate: Optional[str] = None,
                           rdf_object: Optional[str] = None,
                           recursive: bool = True):
        with h5py.File(self.filename, 'r') as h5:
            return list(ObjDB(h5).rdf_find(rdf_subject=rdf_subject,
                                           rdf_type=rdf_type,
                                           rdf_predicate=rdf_predicate,
                                           rdf_object=rdf_object,
                                           recursive=recursive))

    def _instance_find_one(self, *args, **kwargs):
        with h5py.File(self.filename, 'r') as h5:
            return ObjDB(h5).find_one(*args, **kwargs)

    @staticmethod
    def find(file_or_filename, *args, **kwargs) -> List[lazy.LazyObject]:
        """Please refer to the docstring of the find method of the ObjDB class"""
        if isinstance(file_or_filename, (h5py.Group, h5py.Dataset)):
            return list(ObjDB(file_or_filename).find(*args, **kwargs))
        else:
            with h5py.File(file_or_filename, 'r') as h5:
                results = list(ObjDB(h5).find(*args, **kwargs))
            return results

    @staticmethod
    def rdf_find(file_or_filename, *args, **kwargs) -> List[lazy.LazyObject]:
        """Please refer to the docstring of the find method of the ObjDB class"""
        if isinstance(file_or_filename, (h5py.Group, h5py.Dataset)):
            return list(ObjDB(file_or_filename).rdf_find(*args, **kwargs))
        else:
            with h5py.File(file_or_filename, 'r') as h5:
                results = list(ObjDB(h5).find(*args, **kwargs))
            return results


class FilesDB(HDF5DBInterface):
    """A database interface for multiple HDF5 files."""

    def __init__(self, filenames: List[Union[str, pathlib.Path]]):
        self.filenames = list(set(pathlib.Path(filename) for filename in filenames))

    @classmethod
    def from_folder(cls,
                    folder: Union[str, pathlib.Path],
                    hdf_suffixes: Union[str, List[str]] = '.hdf',
                    recursive: bool = False):
        """Create a FilesDB from a folder containing HDF5 files.

        Parameters
        ----------
        folder : Union[str, pathlib.Path]
            The folder containing the HDF5 files.
        hdf_suffixes : Union[str, List[str]], optional
            The suffixes of the HDF5 files to scan for, by default '.hdf'
        recursive : bool, optional
            Whether to scan the folder recursively, by default False

        Returns
        -------
        FilesDB
            The FilesDB object
        """
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

    def find_one(self, *args, **kwargs) -> lazy.LazyObject:
        """Call find_one on all the files registered. If more than one file
        contains the object, the first one is returned. If you want to find one per file,
        call find_one_per_file instead."""
        for filename in self.filenames:
            with h5py.File(filename, mode='r') as h5:
                ret = ObjDB(h5).find_one(*args, **kwargs)
                if ret:
                    return ret

    def find(self, *args, **kwargs) -> Generator[lazy.LHDFObject, None, None]:
        """Call find on all the files"""
        for filename in self.filenames:
            with h5py.File(filename, 'r') as h5:
                ret = ObjDB(h5).find(*args, **kwargs)
                for r in ret:
                    yield r
