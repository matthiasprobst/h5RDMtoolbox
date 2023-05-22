"""standard attribute module"""

import h5py
from abc import ABC


# dictionary that holds all registered standard attributes:


class StandardAttribute(ABC):
    """Abstract base class for user-defined standard attributes that are registered after instantiation
    of the HDF5 File object.

    Parameters
    ----------
    parent: h5py.Group or h5py.Dataset
        HDF5 object to which the attribute is to be set

    Examples
    --------
    Say you want to regulate the usage of the std_attr `long_name` in your project, that must be lowercase.
    You can do so by creating a class that inherits from `StandardAttribute` and implements the setter method
    like so:

    .. code-block:: python

        >>> class LongNameAttribute(StandardAttribute):
        ...     name = 'long_name'
        ...
        ...     def set(self, value: str) -> None:
        ...         if not value.is_lower():
        ...             raise ValueError('Long name must be lower case')
        ...         super().set('long_name', value)
        ...
        >>> from h5rdmtoolbox.wrapper.core import Dataset
        >>> LongNameAttribute.register(Dataset)

    Then you can use the std_attr like so:

    .. code-block:: python

        >>> with h5py.File('test.h5', 'w') as f:
        ...     f.attrs.long_name = 'test'
        ...     print(f.attrs.long_name)
        test

    .. warning::

        Don't call `self.parent.attrs[<name>] = <value>` in the set method. If you expose a standard attribute
        to the attribute manager you risk calling the getter methods in an infinite loop. So always use
        `super().set(<value>)`.
    """

    def __init__(self, parent=None):
        self.parent = parent

    @staticmethod
    def validate(name, value, obj=None):
        """validate the value of the attribute"""
        return True

    def set(self, value, target=None, name=None):
        """Set std_attr to HDF5 object. Superclass method is used to avoid
        infinite recursion.

        Parameters
        ----------
        value: str
            Value to be set as attribute of src
        target: h5py.Group or h5py.Dataset
            HDF5 object to which the attribute is to be set
        name: str
            Name of the attribute to be set
        """
        if target is None:
            target = self.parent
        if name is None:
            name = self.get_name()
        # call the h5py AttributeManager (which is the parent class)
        super(type(target.attrs), target.attrs).__setitem__(name, value)

    def get(self, src=None, name=None, default=None):
        """Get std_attr from HDF5 object. Superclass method is used to avoid
        infinite recursion."""
        if src is None:
            src = self.parent
        if name is None:
            name = self.get_name()
        try:
            return super(type(src.attrs), src.attrs).__getitem__(name)
        except KeyError:
            return default

    def get_name(self) -> str:
        """Get name of the std_attr. If the std_attr has no name or is None,
        the class name is returned."""
        if hasattr(self, 'name'):
            name = self.name
            if name is None:
                return self.__class__.__name__
            return name
        return self.__class__.__name__

    @staticmethod
    def AnyString(attr_name: str):
        class any_string(StandardAttribute):
            name = attr_name

        return any_string
