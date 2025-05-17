"""Implements the protocols for the File Group and Dataset implementations.

Using protocol classes avoids using multiple inheritance and allows for
better code organization. The protocols are used to define the methods that
the classes must implement, and the classes that implement the protocols
must have the same method signatures.
"""

import pathlib
from abc import abstractmethod
from typing import Protocol, Optional, Union, Dict, List, Any, Tuple

import h5py
import numpy as np
import rdflib
import xarray as xr


class NamedObject(Protocol):
    """Protocol for the NamedClass class."""

    filename: pathlib.Path

    @property
    def name(self) -> str:
        """Return the name of the object."""
        ...


class LazyObject(Protocol):
    """Protocol for the LHDFObject class."""

    name: str
    filename: pathlib.Path

    def __lt__(self, other) -> bool:
        """Return the comparison between two objects."""
        ...

    def __eq__(self, other):
        """Return the equality between two objects."""
        ...

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

    @property
    def basename(self) -> str:
        """Return the basename of the object."""
        ...

    @property
    def dtype(self) -> str:
        """Return the dtype of the object."""
        ...

    @property
    def parentname(self) -> str:
        """Return the parent name of the object path."""
        ...

    @property
    def parentnames(self) -> List[str]:
        """Return the parent names of the object path."""
        ...

    @property
    def attrs(self) -> Dict:
        """Return the attributes"""
        ...

    @property
    def hdf_filename(self) -> pathlib.Path:
        """Return the hdf filename."""
        ...


class LazyDataset(LazyObject):
    """Lazy Dataset Protocol class"""

    def __init__(self, obj: h5py.Dataset):
        ...

    def __getitem__(self, item):
        """Return the item by the item name or index"""
        ...

    def coords(self):
        """Return the coordinates associated to the Dataset"""
        ...

    def isel(self, **indexers: Dict):
        """Return the Dataset indexed by the indexers"""
        ...

    def sel(self, **coords: Dict):
        """Return the Dataset selected by the coordinates"""
        ...


class LazyGroup(LazyObject):

    def __init__(self, obj: h5py.Group):
        ...

    def keys(self):
        """Return the keys of the group which are the names of datasets and groups"""
        ...

    def __getitem__(self, item: str) -> LazyObject:
        """Return the dataset or group by the item name"""
        ...


class H5TbxAttributeManager(Protocol):
    """Protocol for the AttributeManager class."""
    _parent: Union[h5py.Group, h5py.Dataset]

    @property
    def raw(self) -> h5py.AttributeManager:
        ...

    def pop(self, key: str, default=None):
        ...

    def get(self, key: str, default=None):
        ...

    def __setitem__(self, name: Union[str, Tuple[str, str]],
                    value, attrs: Optional[Dict] = None):
        ...

    def __getitem__(self, name: str):
        ...

    def create(self,
               name,
               data,
               shape=None, dtype=None,
               rdf_predicate: Union[str, rdflib.URIRef] = None,
               rdf_object: Optional[Union[str, rdflib.URIRef]] = None,
               definition: Optional[str] = None) -> Any:
        ...

    @property
    def parent(self):
        ...


class H5TbxHLObject(Protocol):
    name: str

    @property
    def rootparent(self):
        ...

    @property
    def hdf_filename(self) -> pathlib.Path:
        """Return the filename as a pathlib.Path object."""

    @property
    def attrs(self) -> H5TbxAttributeManager:
        """Return the attributes"""
        ...

    def __delitem__(self, key): ...

    # def __getitem__(self, *args, **kwargs):
    #     ...


class H5TbxFile(H5TbxHLObject):
    """Protocol for the h5tbx.File class."""


class H5TbxGroup(H5TbxFile):
    """Protocol for the h5tbx.Group class."""

    def __getitem__(self, name: str):
        ...

    @property
    @abstractmethod
    def basename(self) -> str:
        """Return the basename, which is the last part
        of the HDF5 object path."""

    @property
    @abstractmethod
    def rdf(self):
        ...


class H5TbxDataset(H5TbxHLObject):
    """Protocol for the h5tbx.Dataset class."""
    name: str

    @property
    @abstractmethod
    def coords(self):
        ...

    @property
    @abstractmethod
    def rdf(self):
        ...

    @property
    @abstractmethod
    def hdf_filename(self) -> pathlib.Path:
        """Return the filename as a pathlib.Path object."""

    @property
    @abstractmethod
    def basename(self) -> str:
        """Return the basename, which is the last part
        of the HDF5 object path."""

    def sel(self, method=None, **coords) -> xr.DataArray:
        """Return the Dataset selected by the coordinates"""
        ...

    def isel(self, **indexers) -> xr.DataArray:
        """Return the Dataset indexed by the indexers"""
        ...

    def make_scale(self, name: str = ''):
        ...

    def __getitem__(self,
                    args,
                    new_dtype=None,
                    nparray=False,
                    links_as_strings: bool = False) -> Union[xr.DataArray, np.ndarray]:
        """Return the data array by the item name"""
        ...


class StandardAttribute(Protocol):

    def get(self, parent) -> str: ...
