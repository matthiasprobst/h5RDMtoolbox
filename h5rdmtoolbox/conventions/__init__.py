""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)
The standrd name definitions (name, description, units) are to be provided in XML files. Two xml files
are provided by this sub-packages (fluid and piv). As the projec is under development, they are generated
in the fluid.py file but in later versions the conventions will only be provided as xml files.
"""

import h5py
from typing import Callable, List, Union, Iterable

from . import standard_attribute
from . import units, long_name, standard_name, title, comment, references, source, respuser
from ._logger import logger
from .layout import H5Layout
from .standard_attribute import StandardAttribute
from .standard_name import StandardName, StandardNameTable
from .utils import dict2xml, is_valid_email_address

__all__ = ['units', 'long_name', 'standard_name', 'title', 'comment', 'references', 'source', 'respuser']


def list_standard_attributes(obj: Callable = None):
    """List all registered standard attributes

    Returns
    -------
    List[StandardAttribute]
        List of all registered standard attributes
    """
    if None:
        return standard_attribute.cache.REGISTERED_PROPERTIES
    return standard_attribute.cache.REGISTERED_PROPERTIES.get(type(obj), {})


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


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


registered_conventions = {}


class Convention:
    """A convention is a set of standard attributes that are used to describe the data in a file."""

    def __init__(self, name):
        self.name = name
        self._properties = {}
        self._methods = {'init_file': {},
                         'create_group': {},
                         'create_dataset': {}}

    def add(self,
            attr_cls: StandardAttribute,
            target_cls: Callable,
            add_to_method: bool = False,
            position: dict = None,
            optional: bool = False,
            default_value: str = None,
            name: str = None,
            overwrite: bool = False
            ):
        from .standard_attribute import register
        if name is None:
            if hasattr(attr_cls, 'name'):
                name = attr_cls.name
            else:
                name = attr_cls.__name__

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

        for cls in target_cls:
            if hasattr(cls, '__get_cls__'):
                cls = type(cls())
            if not issubclass(cls, (h5py.File, h5py.Group, h5py.Dataset)) and not hasattr(cls, '__get_cls__'):
                raise TypeError(f'{cls} is not a valid HDF5 class')

            if cls not in self._properties:
                self._properties[cls] = {}

            if overwrite and name in self._properties[cls]:
                del self._properties[cls][name]

            if name in self._properties[cls] and not overwrite:
                raise AttributeError(
                    f'Cannot register property {name} to {_cls} because it has already a property with this name.')
            self._properties[cls][name] = attr_cls
            logger.debug(f'Register special hdf std_attr {name} to {cls}')

            if add_to_method:
                from ..wrapper.core import Dataset, Group, File
                import forge
                if Dataset in cls.__mro__:
                    if name not in self._methods['create_dataset']:
                        self._methods['create_dataset'][name] = {'cls': cls,
                                                                 'optional': optional,
                                                                 'default': default_value,
                                                                 'position': position}
                    continue
                if File in cls.__mro__:
                    if name not in self._methods['init_file']:
                        self._methods['init_file'][name] = {'cls': cls,
                                                            'optional': optional,
                                                            'default': default_value,
                                                            'position': position}
                    continue
                if Group in cls.__mro__:
                    if name not in self._methods['create_group']:
                        self._methods['create_group'][name] = {'cls': cls,
                                                               'optional': optional,
                                                               'default': default_value,
                                                               'position': position}

    def _add_signature(self):
        import forge
        for name, values in self._methods['create_dataset'].items():
            from ..wrapper.core import Group
            Group.create_dataset = forge.insert(forge.arg(f'{name}', default=values['default']),
                                                **values['position'])(Group.create_dataset)
        for name, values in self._methods['create_group'].items():
            from ..wrapper.core import Group
            Group.create_group = forge.insert(forge.arg(f'{name}', default=values['default']),
                                              **values['position'])(Group.create_group)
        for name, values in self._methods['init_file'].items():
            from ..wrapper.core import File
            File.__init__ = forge.insert(forge.arg(f'{name}', default=values['default']),
                                         **values['position'])(File.__init__)

    def _delete_signature(self):
        import forge
        for name, values in self._methods['create_dataset'].items():
            from ..wrapper.core import Group
            Group.create_dataset = forge.delete(f'{name}')(Group.create_dataset)
        for name, values in self._methods['create_group'].items():
            from ..wrapper.core import Group
            Group.create_group = forge.delete(f'{name}')(Group.create_group)
        for name, values in self._methods['init_file'].items():
            from ..wrapper.core import File
            File.__init__ = forge.delete(f'{name}')(File.__init__)

    def register(self):
        registered_conventions[self.name] = self


def use(convention_name: str) -> None:
    """Use a convention by name"""
    global current_convention
    if convention_name is None:
        convention_name = 'h5py'
    if convention_name not in registered_conventions:
        raise ValueError(f'Convention "{convention_name}" is not registered')
    if current_convention is not None:
        if convention_name == current_convention.name:
            return  # nothing to do
        current_convention._delete_signature()
    current_convention = registered_conventions[convention_name]
    current_convention._add_signature()


current_convention: Union[None, Convention] = None

datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'
__all__ = ['H5Layout', 'datetime_str', 'set_loglevel',
           'StandardName', 'StandardNameTable', 'StandardAttribute']
