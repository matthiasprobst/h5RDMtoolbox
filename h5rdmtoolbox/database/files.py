import h5py
import numpy as np
import os
import pandas as pd
import pathlib
from itertools import chain
from typing import List, Union, Dict, Tuple

from .file import find


class H5Objects:

    def __init__(self, h5objdict: Dict):
        self.h5objdict = h5objdict
        # TODO: check if all are the same object type!

    @property
    def names(self) -> List[str]:
        """Names of objects"""
        return list(self.h5objdict.keys())

    @property
    def shapes(self) -> Tuple[Tuple]:
        """Shapes of objects"""
        return tuple(v.shape for v in self.h5objdict.values())

    @property
    def ndims(self) -> Tuple[int]:
        """Dimensions of objects"""
        return tuple(v.ndim for v in self.h5objdict.values())

    @property
    def basenames(self) -> List[str]:
        """Names of objects"""
        return [os.path.basename(obj.name) for obj in self.h5objdict.values()]

    def __getitem__(self, item):
        if isinstance(self.h5objdict[list(self.h5objdict.keys())[0]], h5py.Dataset):
            return DatasetValues({k: v.values[item] for k, v in self.h5objdict.items()})
        raise TypeError('Cannot slice hdf group objects')


class DatasetValues:

    def __init__(self, arr: Dict):
        self.arr = arr

    def to_dataframe(self, axis=0, join='outer') -> pd.DataFrame:
        """alias for to_DataFrame()"""
        return self.to_DataFrame(axis=axis, join=join)

    def to_DataFrame(self, axis=0, join='outer') -> pd.DataFrame:
        """Return DataFrame. Only works for 1D data!"""
        if np.all([a[:].ndim == 1 for a in self.arr.values()]):
            keys = [os.path.dirname(k) for k in list(self.arr.keys())]
            frames = [pd.DataFrame({os.path.basename(k): v[:]}) for k, v in self.arr.items()]
            return pd.concat(frames, axis=axis, join=join, keys=keys)
        raise ValueError('to_DataFrame() only works with 1D data')


class Files:
    """File-like interface for multiple HDF Files"""

    def __init__(self, filenames: List[Union[str, pathlib.Path]], file_instance=None, **kwargs):
        """
        Parameters
        ----------
        filenames: List[Union[str, pathlib.Path]]
            A list of hdf5 filenames or path to a directory containing hdf files.
            If a directory is passed, the glob-str can be specified via **kwargs.
            Default is glob='*.hdf'.
        file_instance: h5py.File
            The HDF5 file instance
        """
        if file_instance is None:
            from . import File
            file_instance = File

        def _check_dir(fname: pathlib.Path):
            if not fname.is_dir():
                raise ValueError('A single value passed for the parameter "filenames" must be '
                                 'a directory.')
            return True

        isdir = False
        if isinstance(filenames, (str, pathlib.Path)):
            filenames = pathlib.Path(filenames)
            # must be a directory
            isdir = _check_dir(filenames)
        elif isinstance(filenames, (list, tuple)):
            if len(filenames) == 1:
                filenames = pathlib.Path(filenames[0])
                # must be a directory
                isdir = _check_dir(filenames)

        if isdir:
            _filenames = list(pathlib.Path(filenames).glob(kwargs.pop('glob', '*.hdf')))
            if len(_filenames) == 0:
                raise FileNotFoundError(f'No files found in directory: {filenames}')
            self._list_of_filenames = _filenames
        else:
            self._list_of_filenames = [pathlib.Path(f) for f in filenames]
            for fname in self._list_of_filenames:
                if fname.is_dir():
                    raise ValueError(f'Expecting filenames not directory names but "{fname}" is.')

        self._opened_files = {}
        self._file_instance = file_instance

    def __getitem__(self, item) -> Union[h5py.Group, H5Objects, List[h5py.Group]]:
        """If integer, returns item-th root-group. If item is string,
        a list of objects of that item is returned"""
        if isinstance(item, int):
            return self._opened_files[list(self.keys())[item]]
        if isinstance(item, (tuple, list)):
            return [self._opened_files[list(self.keys())[i]] for i in item]
        return H5Objects({f'{key}/item': rgrp[item] for key, rgrp in zip(self.keys(), self.values()) if item in rgrp})

    def __enter__(self):
        for filename in self._list_of_filenames:
            try:
                h5file = self._file_instance(filename, mode='r')
                self._opened_files[str(filename)] = h5file
            except RuntimeError as e:
                print(f'RuntimeError: {e}')
                for h5file in self._opened_files.values():
                    h5file.close()
                self._opened_files = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._opened_files = {}
        self.close()

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        return f'<{self.__class__.__name__} ({self.__len__()} files)>'

    def __str__(self):
        return f'<{self.__class__.__name__} ({self.__len__()} files)>'

    def find_one(self, flt: Union[Dict, str],
                 objfilter=None,
                 rec: bool = True,
                 ignore_attribute_error: bool = False) -> Union[h5py.Group, h5py.Dataset, None]:
        """See find() in h5file.py"""
        for v in self.values():
            found = find(v, flt, objfilter=objfilter, recursive=rec, find_one=True,
                         ignore_attribute_error=ignore_attribute_error)
            if found:
                return found

    def find(self, flt: Union[Dict, str], objfilter=None, rec: bool = True, ignore_attribute_error: bool = False):
        """See find() in h5file.py"""
        found = [find(v, flt, objfilter=objfilter, recursive=rec, find_one=False,
                      ignore_attribute_error=ignore_attribute_error) for
                 v in self.values()]
        return list(chain.from_iterable(found))

    def keys(self):
        """Return all opened filename stems"""
        return self._opened_files.keys()

    def values(self):
        """Return all group instances in the file stems"""
        return self._opened_files.values()

    def close(self):
        """Close all opened files"""
        for h5file in self._opened_files.values():
            h5file.close()
