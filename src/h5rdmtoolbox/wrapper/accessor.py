"""Module to register attributes of wrapper classes without touching the implementation"""
import logging
from typing import Union, Type

from h5rdmtoolbox.protocols import H5TbxHLObject

logger = logging.getLogger('h5rdmtoolbox')


class SpecialDatasetRegistrationWarning(Warning):
    """Warning for special dataset registration"""


class _CachedHDFAccessor:
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


PROPERTY_ACCESSOR_NAMES = []


def _register_accessor(name, cls, special_dataset, overwrite):
    if hasattr(cls, name):
        if not overwrite:
            raise RuntimeError(f'Cannot register the accessor {special_dataset!r} under name {name!r} '
                               f'because it already exists and overwrite is set to {overwrite}')
    logger.debug(f'Registering special dataset {name!r} for class {cls!r}')
    setattr(cls, name, _CachedHDFAccessor(name, special_dataset))
    return special_dataset


def register_accessor(name, cls: Union[str, Type[H5TbxHLObject]], overwrite=False):
    """registers a special dataset to a wrapper class"""

    if isinstance(cls, str):
        if cls.lower() == 'dataset':
            from .core import Dataset
            cls = Dataset
        elif cls.lower() == 'group':
            from .core import Group
            cls = Group
        elif cls.lower() == 'file':
            from .core import File
            cls = File
        else:
            raise ValueError(f'Invalid class type {cls!r}')

    def decorator(accessor):
        """decorator"""
        return _register_accessor(name, cls, accessor, overwrite)

    return decorator


class Accessor:
    """Base class for all special datasets"""

    def __init__(self, obj: H5TbxHLObject):
        """Initialize the accessor with the object to be accessed

        Parameters
        ----------
        obj : H5TbxHLObject
            The object to which the accessor is attached
        """
        self._obj = obj
