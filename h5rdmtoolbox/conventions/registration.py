"""
Contains all property accessors

the python filename and accessor class name must not be identical!
"""

import h5py
from typing import Union, Any

from ._logger import logger

# dictionary of all registered user-defined attribute names
REGISTERED_PROPERTIES = {}


class UserAttr:
    """Base class for user-defined attributes that are registered after instantiation
    of the HDF5 File object
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

    def deleter(self, obj: Union[h5py.Dataset, h5py.Group]):
        """Delete attribute from HDF5 object

        Parameters
        ----------
        obj: h5py.AttributeManager
            HDF5 AttributeManager object from which the attribute is deleted
        """
        obj.attrs.__delitem__(self.name)


def validate_user_hdf_attribute(obj, methods=('getter', 'setter', 'deleter', 'safe_getter', 'safe_setter')):
    """validate that the user-defined attribute has the required methods"""
    for method in methods:
        if not hasattr(obj, method):
            raise AttributeError(f'obj {obj} must have a "{method}" method')
    return True


def _register_hdf_attribute(cls, name: str = None, overwrite: bool = False):
    def decorator(accessor):
        """decorator"""
        validate_user_hdf_attribute(accessor)
        a = accessor()
        if cls not in REGISTERED_PROPERTIES:
            REGISTERED_PROPERTIES[cls] = {}
        if name in REGISTERED_PROPERTIES[cls] and not overwrite:
            raise ValueError(f'Attribute {name} is already registered for {cls}')
        REGISTERED_PROPERTIES[cls][name] = a
        return register_hdf_attribute(a, cls, name, overwrite)

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
    return _register_hdf_attribute(cls, name=name, overwrite=overwrite)


def register_hdf_attribute(attribute, cls, name=None, overwrite=False):
    """register an attribute defined in `attribute_class` to `cls`

    Parameters
    ----------
    attribute: UserAttr
        User-defined attribute. Must be a subclass of `UserAttr`
    cls: Dataset or Group
        HDF5 object to attach standard attribute to.
    name: str, default=None
        Name to be used for the attribute. If None, `attribute.name` is used. If no `attribute.name` is available
        or is None, `attribute.__class__.__name__` is used
    overwrite: bool, default=False
        Whether to overwrite an existing attributes


    Examples
    --------
    >>> class MyAttr(UserAttr):
    ...     name = 'my_attr'
    ...     def getter(self, obj):
    ...         # add 1 to the value
    ...         return self.value(obj) + 1
    >>> # register my attribute to a Group:
    >>> register_hdf_attribute(MyAttr(), cls=Group)
    """

    if not isinstance(attribute, UserAttr):
        raise TypeError(f'Cannot register property {attribute} to {cls} because it is not a '
                        'UserAttr instance.'
                        )

    # figure out the name of the attribute:
    if name is None:
        if hasattr(attribute, 'name'):
            name = attribute.name
            if name is None:
                name = attribute.__class__.__name__
        else:
            name = attribute.__class__.__name__

    if cls not in REGISTERED_PROPERTIES:
        REGISTERED_PROPERTIES[cls] = {}

    if name in REGISTERED_PROPERTIES[cls] and not overwrite:
        raise AttributeError(
            f'Cannot register property {name} to {cls} because it has already a property with this name.')
    REGISTERED_PROPERTIES[cls][name] = attribute
    logger.debug(f'Register special hdf attribute {name} to {cls}')
    return attribute
