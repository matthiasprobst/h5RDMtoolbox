import h5py
import warnings
from abc import ABC
from typing import Union, Callable, Iterable, Any, Dict

from ._logger import logger
# dictionary that holds all registered standard attributes:
from .. import cache


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

    @classmethod
    def register(cls,
                 convention_name: str,
                 target_cls: Union[Callable, Iterable[Callable]],
                 add_to_method: bool = True,
                 optional: bool = False,
                 method_default_value: Any = None,
                 position: Dict = {'index': -1},
                 name: str = None, overwrite: bool = False):
        """Register the standard std_attr to a HDF5 class (File, Group, Dataset)"""
        if name is None:
            if hasattr(cls, 'name'):
                name = cls.name
            else:
                name = cls.__name__
        register(convention_name, cls, target_cls, name, overwrite)
        if add_to_method:
            from ..wrapper.core import Dataset, Group, File
            import forge

            convention_cache = cache.cache[convention_name]

            if Dataset in target_cls.__mro__:
                # if target_cls is a subclass of Dataset then standard argument
                # may be required during create_dataset:
                if name not in convention_cache.methods['create_dataset']:
                    Group.create_dataset = forge.insert(forge.arg(f'{name}', default=method_default_value),
                                                        **position)(Group.create_dataset)
                    convention_cache.methods['create_dataset'][name] = {'cls': cls, 'optional': optional}
            elif File in target_cls.__mro__:
                if name not in convention_cache.methods['init_file']:
                    File.__init__ = forge.insert(forge.arg(f'{name}', default=method_default_value),
                                                 **position)(File.__init__)
                    convention_cache.methods['init_file'][name] = {'cls': cls, 'optional': optional}
            elif Group in target_cls.__mro__:
                if name not in convention_cache.methods['init_group']:
                    Group.create_group = forge.insert(forge.arg(f'{name}', default=method_default_value),
                                                      **position)(Group.create_dataset)
                    convention_cache.methods['create_group'][name] = {'cls': cls, 'optional': optional}

        # if target_methods is not None:
        #     register_method(name, target_methods, overwrite)


def _parse_name(name: str, attribute: Callable) -> str:
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


def register_method(name,
                    target_meth: Union[Callable, Iterable[Callable]],
                    overwrite=False) -> None:
    import forge
    """Register the standard attribute for a class method"""
    if not isinstance(target_meth, Iterable):
        target_meth = [target_meth]
    for meth in target_meth:
        meth = forge.insert(forge.arg(f'{name}', default=None), index=6)(meth)
        convention_cache.methods[meth] = name


def register(convention_name: str,
             attr_cls,
             target_cls: Union[Callable, Iterable[Callable]],
             name=None,
             overwrite=False) -> None:
    """register a std_attr defined in `attribute_class` to `cls`

    Parameters
    ----------
    attr_cls: StandardAttribute
        User-defined std_attr. Must be a subclass of `StandardAttribute`
    target_cls: Union[Callable, Iterable[Callable]]
        HDF5 object or Iterable of HDF5 objects to attach standard std_attr to. Valid objects
        are `h5py.Dataset`, `h5py.Group` and `h5py.File`
    name: str, default=None
        Name to be used for the std_attr. If None, `std_attr.name` is used. If no `std_attr.name` is available
        or is None, `std_attr.__class__.__name__` is used
    overwrite: bool, default=False
        Whether to overwrite an existing attributes

    Returns
    -------
    None

    Examples
    --------
    >>> class MyAttr(StandardAttribute):
    ...     name = 'my_attr'
    ...     def get(self):
    ...         # add 1 to the value
    ...         return super().get() + 1
    >>> # register my std_attr to a Group:
    >>> register_standard_attribute(MyAttr(), cls=Group)
    """

    if not hasattr(attr_cls, 'set') and not hasattr(attr_cls, 'get'):
        raise TypeError(f'Cannot register standard attribute {attr_cls} to {target_cls} because it does not '
                        'have a getter and setter method.')
    if StandardAttribute not in attr_cls.__bases__:
        raise TypeError(f'Cannot register standard attribute {attr_cls} to {target_cls} because it is not a '
                        'subclass of `StandardAttribute`.')

    # figure out the name of the std_attr:
    name = _parse_name(name, attr_cls)

    if not isinstance(target_cls, Iterable):
        # make it a list
        target_cls = [target_cls]

    def _register(_cls):
        convention_cache = cache.cache[convention_name]
        if _cls not in convention_cache.properties:
            convention_cache.properties[_cls] = {}

        if name in convention_cache.properties[_cls] and not overwrite:
            warnings.warn(
                f'Cannot register property {name} to {_cls} because it has already a property with this name.',
                UserWarning)
            # raise AttributeError(
            #     f'Cannot register property {name} to {_cls} because it has already a property with this name.')
        convention_cache.properties[_cls][name] = attr_cls
        logger.debug(f'Register special hdf std_attr {name} to {_cls}')

    for c in target_cls:
        if hasattr(c, '__get_cls__'):
            c = type(c())
        if not issubclass(c, (h5py.File, h5py.Group, h5py.Dataset)) and not hasattr(c, '__get_cls__'):
            raise TypeError(f'{c} is not a valid HDF5 class')
        _register(c)
