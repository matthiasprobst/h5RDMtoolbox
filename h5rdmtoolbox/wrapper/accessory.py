"""Module to register attributes of wrapper classes without touching the implementation"""
import h5py
from typing import Union

from .core import H5Group, H5File
from ..xr.dataset import HDFXrDataset


class SpecialDatasetRegistrationWarning(Warning):
    """Warning for special dataset registration"""


class _CachedAccessor:
    """Custom property-like object (descriptor) for caching accessors."""

    def __init__(self, name, accessor):
        self._name = name
        self._accessor = accessor

    def __get__(self, obj, cls):
        if obj is None:
            # we're accessing the attribute of the class, i.e., Dataset.geo
            return self._accessor

        # Use the same dict as @pandas.util.cache_readonly.
        # It must be explicitly declared in obj.__slots__.
        try:
            cache = obj._cache
        except AttributeError:
            cache = obj._cache = {}

        try:
            return cache[self._name]
        except KeyError:
            pass

        try:
            accessor_obj = self._accessor(obj)
        except AttributeError as exc:
            # __getattr__ on data object will swallow any AttributeErrors
            # raised when initializing the accessor, so we need to raise as
            # something else (GH933):
            raise RuntimeError(f"error initializing {self._name!r} accessor.") from exc

        cache[self._name] = accessor_obj
        return accessor_obj


# def _register_special_dataset(name, cls, overwrite):
#     def decorator(accessor):
#         """decorator"""
#         if hasattr(cls, name):
#             if overwrite:
#                 pass
#                 # warnings.warn(
#                 #     f"registration of accessor {accessor!r} under name {name!r} for type {cls!r} is "
#                 #     "overriding a preexisting attribute with the same name.",
#                 #     SpecialDatasetRegistrationWarning,
#                 #     stacklevel=2,
#                 # )
#             else:
#                 raise RuntimeError(f'Cannot register the accessor {accessor!r} under name {name!r} '
#                                    f'because it already exists and overwrite is set to {overwrite}')
#         setattr(cls, name, _CachedAccessor(name, accessor))
#         return accessor
#
#     return decorator


PROPERTY_ACCESSOR_NAMES = []


def _register_special_dataset(name, cls, special_dataset, overwrite):
    if hasattr(cls, name):
        if not overwrite:
            raise RuntimeError(f'Cannot register the accessor {special_dataset!r} under name {name!r} '
                               f'because it already exists and overwrite is set to {overwrite}')
    setattr(cls, name, _CachedAccessor(name, special_dataset))
    return special_dataset


def register_special_dataset(name, cls: Union["H5Dataset", "H5Group"], overwrite=False):
    """registers a special dataset to a wrapper class"""

    def decorator(accessor):
        """decorator"""
        return _register_special_dataset(name, cls, accessor, overwrite)

    return decorator


class Accessor:
    """Base class for all special datasets"""

    def __init__(self, h5grp: h5py.Group):
        self._grp = h5grp


@register_special_dataset("Vector", H5Group)
@register_special_dataset("Vector", H5File)
class VectorDataset(Accessor):
    """A special dataset for vector data.
     The vector components are stored in the group as datasets."""

    def __init__(self, h5grp: h5py.Group):
        self._grp = h5grp

    def __call__(self, *args, **kwargs) -> HDFXrDataset:
        """Returns a xarray dataset with the vector components as data variables."""
        if len(args) and len(kwargs):
            raise ValueError('Either args or kwargs must be provided but not both')
        hdf_datasets = {}
        for arg in args:
            if isinstance(arg, str):
                ds = self._grp[arg]
            elif isinstance(arg, h5py.Dataset):
                ds = arg
            else:
                raise TypeError(f'Invalid type: {type(arg)}')
            hdf_datasets[ds.name.strip('/')] = ds

        for name, ds in kwargs.items():
            if not isinstance(ds, h5py.Dataset):
                raise TypeError(f'Invalid type: {type(ds)}')
            hdf_datasets[name.strip('/')] = ds

        return HDFXrDataset(**hdf_datasets)
