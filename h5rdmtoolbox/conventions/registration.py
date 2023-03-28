"""
Contains all property accessors

the python filename and accessor class name must not be identical!
"""

import h5py
from abc import ABC
from typing import Union, Any, Callable

from ._logger import logger

# dictionary of all registered user-defined attribute names
REGISTERED_PROPERTIES = {}


def parse(name: str, attribute: Callable) -> str:
    """Parse name of the attribute. If the attribute has no name or is None,
    the class name is returned."""
    if name is None:
        if hasattr(attribute, 'name'):
            name = attribute.name
            if name is None:
                name = attribute.__class__.__name__
        else:
            name = attribute.__class__.__name__
    return name


class StandardAttribute(ABC):
    """Abstract base class for user-defined standard attributes that are registered after instantiation
    of the HDF5 File object.

    Examples
    --------
    Say you want to regulate the usage of the attribute `long_name` in your project, that must be lowercase.
    You can do so by creating a class that inherits from `StandardAttribute` and implements the setter method
    like so:
    >>> class LongNameAttribute(StandardAttribute):
    ...     name = 'long_name'
    ...
    ...     def setter(self, obj, value: str) -> None:
    ...         if not value.is_lower():
    ...             raise ValueError('Long name must be lower case')
    ...         obj.attrs.create('long_name', value)
    ...
    >>> register_attribute(LongNameAttribute)
    Then you can use the attribute like so:
    >>> with h5py.File('test.h5', 'w') as f:
    ...     f.attrs.long_name = 'test'
    ...     print(f.attrs.long_name)
    test

    .. warning::

        If you expose a standard attribute to be the attribute manager you risk calling the
        getter methods in an infinite loop. So don't do
        >>> obj.attrs[self.name]
        but
        >>> obj.safe_getter(self.name)
        The latter calls the superclass method and hence avoids infinite recursion.
    """

    def safe_setter(self, obj, value):
        """Set attribute to HDF5 object. Superclass method is used to avoid
        infinite recursion."""
        super(type(obj.attrs), obj.attrs).__setitem__(self.get_name(), value)

    @staticmethod
    def safe_attr_getter(obj, name, default=None):
        """Get attribute from HDF5 object. Superclass method is used to avoid
        infinite recursion."""
        try:
            return super(type(obj.attrs), obj.attrs).__getitem__(name)
        except KeyError:
            return default

    def safe_getter(self, obj, default=None):
        """Get attribute from HDF5 object. Superclass method is used to avoid
        infinite recursion."""
        try:
            return super(type(obj.attrs), obj.attrs).__getitem__(self.get_name())
        except KeyError:
            return default

    def get_name(self) -> str:
        """Get name of the attribute. If the attribute has no name or is None,
        the class name is returned."""
        if hasattr(self, 'name'):
            name = self.name
            if name is None:
                return self.__class__.__name__
            return name
        return self.__class__.__name__

    def setter(self, obj: Union[h5py.Dataset, h5py.Group], value: Any):
        """Set attribute to HDF5 object

        Parameters
        ----------
        obj: h5py.AttributeManager
            HDF5 AttributeManager object to which the attribute is set
        value: Any
            Value of the attribute
        """
        obj.attrs.create(self.get_name(), value)

    def getter(self, obj: Union[h5py.Dataset, h5py.Group]):
        """Get attribute from HDF5 object

        Parameters
        ----------
        obj: h5py.AttributeManager
            HDF5 AttributeManager object from which the attribute is retrieved

        Returns
        -------
        Any
            Value of the attribute
        """
        return self.safe_getter(obj)


def validate_standard_attribute_class(obj, methods=('getter', 'setter', 'safe_getter', 'safe_setter')):
    """validate that the user-defined attribute has the required methods"""
    for method in methods:
        if not hasattr(obj, method):
            raise AttributeError(f'obj {obj} must have a "{method}" method')
    return True


def _register_standard_attribute(cls, name: str = None, overwrite: bool = False):
    def decorator(accessor):
        """decorator"""
        validate_standard_attribute_class(accessor)

        a = accessor()

        if cls not in REGISTERED_PROPERTIES:
            REGISTERED_PROPERTIES[cls] = {}

        _name = parse(name, a)
        if _name in REGISTERED_PROPERTIES[cls] and not overwrite:
            raise ValueError(f'Attribute {_name} is already registered for {cls}')

        REGISTERED_PROPERTIES[cls][_name] = a
        return register_standard_attribute(a, cls, _name, overwrite)

    return decorator


def register_hdf_attr(cls: Union["Dataset", "Group"], overwrite=False, name: str = None):
    """registers a property to a group or dataset. getting method must be specified, setting and deleting are optional,
    also docstring is optional but strongly recommended!

    Parameters
    ----------
    cls: Dataset or Group
        HDF5 object to attach standard attribute to.
    overwrite: bool, default=False
        Whether to overwrite an existing attributes
    name: str, default=None
        Name to be used for the attribute. If None, cls.__name__ is used
    """
    return _register_standard_attribute(cls, name=name, overwrite=overwrite)


def register_standard_attribute(attribute, cls, name=None, overwrite=False):
    """register an attribute defined in `attribute_class` to `cls`

    Parameters
    ----------
    attribute: StandardAttribute
        User-defined attribute. Must be a subclass of `StandardAttribute`
    cls: Dataset or Group
        HDF5 object to attach standard attribute to.
    name: str, default=None
        Name to be used for the attribute. If None, `attribute.name` is used. If no `attribute.name` is available
        or is None, `attribute.__class__.__name__` is used
    overwrite: bool, default=False
        Whether to overwrite an existing attributes


    Examples
    --------
    >>> class MyAttr(StandardAttribute):
    ...     name = 'my_attr'
    ...     def getter(self, obj):
    ...         # add 1 to the value
    ...         return self.value(obj) + 1
    >>> # register my attribute to a Group:
    >>> register_standard_attribute(MyAttr(), cls=Group)
    """

    if not isinstance(attribute, StandardAttribute):
        raise TypeError(f'Cannot register property {attribute} to {cls} because it is not a '
                        'StandardAttribute instance.'
                        )

    # figure out the name of the attribute:
    name = parse(name, attribute)

    if cls not in REGISTERED_PROPERTIES:
        REGISTERED_PROPERTIES[cls] = {}

    if name in REGISTERED_PROPERTIES[cls] and not overwrite:
        raise AttributeError(
            f'Cannot register property {name} to {cls} because it has already a property with this name.')
    REGISTERED_PROPERTIES[cls][name] = attribute
    logger.debug(f'Register special hdf attribute {name} to {cls}')
    return attribute
