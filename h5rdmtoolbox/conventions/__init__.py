""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)
The standard name definitions (name, description, units) are to be provided in XML files. Two xml files
are provided by this sub-packages (fluid and piv). As the project is under development, they are generated
in the fluid.py file but in later versions the conventions will only be provided as xml files.
"""
import forge
import h5py
import inspect
import pathlib
import yaml
from typing import Callable, Union, List

from . import errors
from ._logger import logger
from .layout import Layout, validators
from .layout.validators import Validator
from .standard_attributes import StandardAttribute, __doc_string_parser__
from .._repr import make_italic, make_bold
from ..utils import download_zenodo_file

__all__ = ['Layout', 'validators', 'Validator', 'Convention']


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


registered_conventions = {}


class Convention:
    """Convention class

    Parameters
    ----------
    name : str
        Name of the convention
    contact : str
        ORCID of the researcher
    institution : str, optional
        Institution of the researcher (if different from that of contact)
    use_scale_offset: bool=False
        Whether to enable the scale-offset feature or not. Default is False

    .. note::

        Concept of offset and scale:
        If a dataset has the attribute 'offset' and/or 'scale' (the attribute names can be
        changed by the user using `offset_attribute_name` and `scale_attribute_name`), the
        return value is processed as follows:
        .. math::
            x_{new} = (x \cdot f_{scale}) + f_{offset}
        This behaviour can be disabled by passing `None` to `offset_attribute_name` and/or
        `scale_attribute_name`.
    """
    scale_attribute_name = 'scale'
    offset_attribute_name = 'offset'

    def __init__(self,
                 name: str,
                 contact: str,  # ORCID of researcher
                 institution: str = None,  # only if different than that from contact
                 use_scale_offset: bool = False):
        from ..wrapper.core import File, Group, Dataset

        self.contact = contact
        self.institution = institution

        self._registered_standard_attributes = {}
        self.name = name
        self.use_scale_and_offset = use_scale_offset

        self.properties = {}
        self.methods = {File: {}, Group: {}, Dataset: {}}
        self.method_cls_assignment = {'__init__': File,
                                      'create_group': Group,
                                      'create_dataset': Group,
                                      'create_string_dataset': Group}
        self.property_cls_assignment = {'__init__': File,
                                        'create_group': Group,
                                        'create_dataset': Dataset,
                                        'create_string_dataset': Dataset}

        if self.use_scale_and_offset:
            scale_attr = StandardAttribute(name=self.scale_attribute_name,
                                           validator='$pintquantity',
                                           method='create_dataset',
                                           description='Scale factor for the dataset values.',
                                           optional=True,
                                           position={'after': 'data'},
                                           return_type='pint.Quantity',
                                           default_value=1.0)
            self.add(scale_attr)
            offset_attr = StandardAttribute(name=self.offset_attribute_name,
                                            validator={'$type': (int, float)},
                                            method='create_dataset',
                                            description='Scale factor for the dataset values.',
                                            optional=True,
                                            position={'after': 'data'},
                                            # return_type='pint.Quantity',
                                            default_value=0.0)
            self.add(offset_attr)

            units_attr = StandardAttribute(name='units',
                                           validator='$pintunit',
                                           method='create_dataset',
                                           description='Physical unit of the dataset.',
                                           optional=True,
                                           position={'after': 'data'},
                                           # return_type='pint.Unit',
                                           # return_type='str',
                                           default_value=None)
            self.add(units_attr)
            # self['create_dataset'].add(attr_cls=units.UnitsAttribute,
            #                            # target_cls=Dataset,
            #                            add_to_method=True,
            #                            position={'after': 'data'},
            #                            optional=True)

    def __repr__(self):
        header = f'Convention("{self.name}")'
        out = f'{make_bold(header)}'
        out += f'\ncontact: {self.contact}'

        # header = make_bold('\n> Properties')
        # out += f'{header}:'
        #
        # if len(self.properties) == 0:
        #     out += f' ({make_italic("Nothing registered")})'
        #
        # for obj, properties in self.properties.items():
        #     out += f'\n{obj.__name__}:'
        #     for prop_name, sattr in properties.items():
        #         out += f'\n    * {prop_name}: {sattr.__name__}'

        # header = make_bold('\n> Methods')
        # out += f'{header}:'

        for cls, methods in self.methods.items():
            for name, opts in methods.items():
                out += f'\n  {cls.__name__}.{name}():'
                if len(opts) == 0:
                    out += f' ({make_italic("Nothing registered")})'
                    continue
                # if props exist list them. first required, then optional
                prop_dict = {'optional': {}, 'required': {}}
                for prop_name, prop_opts in opts.items():
                    # for property_name, property_dict in methods.items():
                    if prop_opts['optional']:
                        prop_dict['optional'][prop_name] = prop_opts
                    else:
                        prop_dict['required'][prop_name] = prop_opts

                for prop_name, prop in prop_dict['required'].items():
                    out += f'\n    * {make_bold(prop_name)}: {self._registered_standard_attributes[prop_name].description}'
                for prop_name, prop in prop_dict['optional'].items():
                    out += f'\n    * {make_italic(prop_name)} (default={prop["default"]}): ' \
                           f'{self._registered_standard_attributes[prop_name].description}'
        out += '\n'
        return out

    def __getitem__(self, method):
        # get the class from the method the user wants to add a standard attribute to
        cls = self.method_cls_assignment[method]
        # get the class for which the standard attribute is added as property
        prop = self.property_cls_assignment[method]
        return ConventionInterface(self,
                                   cls=cls,
                                   prop=prop,
                                   method=method)

    @staticmethod
    def from_yaml(yaml_filename, register=True) -> "Convention":
        """Create a convention from a yaml file."""
        return from_yaml(yaml_filename, register=register)

    def add(self, std_attr: StandardAttribute):
        """Add a standard attribute to the convention."""
        _registered_names = list(self._registered_standard_attributes.keys())
        if std_attr.name in _registered_names:
            raise errors.ConventionError(f'A standard attribute with the name "{std_attr.name}" is already registered.')
        if std_attr.requirements is not None:
            if not all(r in _registered_names for r in std_attr.requirements):
                # collect the missing ones:
                _missing_requirements = []
                for r in std_attr.requirements:
                    if r not in _registered_names:
                        _missing_requirements.append(r)
                raise errors.ConventionError(f'Not all requirements for "{std_attr.name}" are registered. '
                                             f'Please add them to the convention first: {_missing_requirements}')

        self._registered_standard_attributes[std_attr.name] = std_attr
        if not isinstance(std_attr.method, (list, tuple)):
            methods = [std_attr.method, ]
        else:
            methods = std_attr.method
        for method in methods:
            if isinstance(method, str):
                method_names = [method, ]
                optionals = [False, ]
            elif isinstance(method, dict):
                method_names = list(method.keys())
                optionals = [m['optional'] for m in method.values()]

            for method_name, optional in zip(method_names, optionals):

                target_cls = self.property_cls_assignment[method_name]
                if target_cls not in self.properties:
                    self.properties[target_cls] = {}
                self.properties[target_cls][std_attr.name] = std_attr

                if target_cls not in self.methods:
                    self.methods[target_cls] = {}

                add_to_method = True
                if add_to_method:
                    cls = self.method_cls_assignment[method_name]
                    if method_name not in cls.__dict__:
                        raise AttributeError(
                            f'Cannot add standard attribute {std_attr.name} to method {method_name} of {target_cls} '
                            'because it does not exist.'
                        )
                    if method_name not in self.methods[cls]:
                        self.methods[cls][method_name] = {}
                    if isinstance(std_attr.method, str):
                        alt = None
                    else:
                        alt = std_attr.method[method_name].get('alt', None)
                    self.methods[cls][method_name][std_attr.name] = {
                        'cls': target_cls,
                        'optional': optional,
                        'default': std_attr.default_value,
                        'position': std_attr.position,
                        'alt': alt
                    }

    def _add(self,
             attr_cls: StandardAttribute,
             target_cls: Callable,
             target_property: str,
             method: str,
             add_to_method: Union[bool, str] = False,
             position: dict = None,
             optional: bool = False,
             alt: str = None,
             default_value: str = None,
             name: str = None,
             overwrite: bool = False
             ):
        """Add a standard attribute to a class and modify signature of the methods if required.

        Parameters
        ----------
        attr_cls : StandardAttribute
            The standard attribute class to be added
        target_cls : Callable
            The class to which the standard attribute is added
        add_to_method : bool, optional
            If True, the standard attribute is added to the signature the respected method, thus it can be
            passed to the method. Depending on the following parameters, the standard attribute is optional
            or required and has a specific default value.
        position : dict, optional
            The position of the standard attribute in the signature of the method.
            E.g. {'index': 1} or {'position': {'after': 'name'}}
        optional : bool, optional
            If True, the standard attribute is optional in the signature of the method.
        alt : str, optional
            The name of an alternative standard attribute that is used if the standard attribute is not provided.
            If neither the standard attribute nor the alternative attribute is provided, an error is raised.
            Only valid if `optional` is False.
        default_value : str, optional
            The default value of the standard attribute in the signature of the method.
        name : str, optional
            The name of the standard attribute. If None, the name of the class is used.
        overwrite : bool, optional
            If True, the standard attribute is overwritten if it already exists.
        """
        if name is None:
            if hasattr(attr_cls, 'name'):
                name = attr_cls.name
            else:
                name = attr_cls.__name__

        if not hasattr(attr_cls, 'set'):
            raise TypeError(f'Cannot register standard attribute {attr_cls} to {target_cls} because it does not '
                            'have a setter method.')

        if not hasattr(attr_cls, 'get'):
            raise TypeError(f'Cannot register standard attribute {attr_cls} to {target_cls} because it does not '
                            'have a getter method.')

        if StandardAttribute not in attr_cls.__bases__:
            raise TypeError(f'Cannot register standard attribute {attr_cls} to {target_cls} because it is not a '
                            'subclass of `StandardAttribute`.')

        if not isinstance(target_cls, (tuple, list)):
            # make it a list
            target_cls = [target_cls]

        for cls in target_cls:
            # if hasattr(cls, '__get_cls__'):
            #     cls = type(cls())
            # if not issubclass(cls, (h5py.File, h5py.Group, h5py.Dataset)) and not hasattr(cls, '__get_cls__'):
            if not issubclass(cls, (h5py.File, h5py.Group, h5py.Dataset)):
                raise TypeError(f'{cls} is not a valid HDF5 class')

            if target_property not in self.properties:
                self.properties[target_property] = {}

            if overwrite and name in self.properties[target_property]:
                del self.properties[target_property][name]

            if name in self.properties[target_property] and not overwrite:
                raise AttributeError(
                    f'Cannot register property {name} to {target_property} because it has already a property with '
                    'this name.')

            self.properties[target_property][name] = attr_cls

            logger.debug(f'Register special hdf std_attr {name} as property to class {target_property}')

            if cls not in self.methods:
                self.methods[cls] = {}

            if method not in self.methods[cls]:
                self.methods[cls][method] = {}

            if add_to_method:
                if method not in cls.__dict__:
                    raise AttributeError(f'Cannot add standard attribute {name} to method {method} of {cls} because it '
                                         f'does not exist.')
                self.methods[cls][method][name] = {'cls': cls,
                                                   'optional': optional,
                                                   'default': default_value,
                                                   'position': position,
                                                   'alt': alt}

    def _add_signature(self):
        for cls, methods in self.methods.items():
            for name, props in methods.items():
                for prop_name, prop_opts in props.items():

                    __doc_string_parser__[cls][name].add_additional_parameters(
                        {prop_name: {'default': prop_opts['default'],
                                     'type': 'str',
                                     'description': self._registered_standard_attributes[
                                         prop_name].description}}
                    )

                    if isinstance(prop_opts['position'], dict):
                        setattr(cls, name, forge.insert(forge.arg(f'{prop_name}',
                                                                  default=prop_opts['default']),
                                                        **prop_opts['position'])(cls.__dict__[name]))
                    else:
                        signature = inspect.signature(cls.__dict__[name])
                        params = [param for param in signature.parameters.values() if
                                  param.kind == inspect.Parameter.KEYWORD_ONLY]
                        if len(params) == 0:
                            params = [param for param in signature.parameters.values() if
                                      param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
                        setattr(cls, name, forge.insert(forge.kwo(f'{prop_name}',
                                                                  default=prop_opts['default'],
                                                                  ),
                                                        after=params[-1].name)(cls.__dict__[name]))
        for cls, methods in self.methods.items():
            for name, props in methods.items():
                __doc_string_parser__[cls][name].update_docstring()

    def _delete_signature(self):
        for cls, methods in self.methods.items():
            for name, props in methods.items():
                for prop_name, prop_attrs in props.items():
                    setattr(cls, name, forge.delete(f'{prop_name}')(cls.__dict__[name]))
                    __doc_string_parser__[cls][name].restore_docstring()
                    # orig_docs[cls][name]['callable'].__doc__ = orig_docs[cls][name]['doc']

    def register(self):
        registered_conventions[self.name] = self

    def _change_attr_prop(self, method_name, attr_name, attr_prop, value):
        for obj in self.methods.values():
            if method_name in obj:
                if attr_name in obj[method_name]:
                    obj[method_name][attr_name][attr_prop] = value
                    return
        raise ValueError(f'Cannot change property {attr_prop} of attribute {attr_name} to {value} '
                         f'for {method_name} because it does not exist.')

    def make_required(self, method_name, attr_name):
        """Make an attribute required for a method"""
        self._change_attr_prop(method_name, attr_name, 'optional', False)

    def make_optional(self, method_name, attr_name):
        """Make an attribute optional for a method"""
        self._change_attr_prop(method_name, attr_name, 'optional', True)


class ConventionInterface:

    def __init__(self,
                 convention: Convention,
                 cls,
                 prop,
                 method):
        self.convention = convention
        self.method = method
        self.prop = prop
        self.cls = cls

    def add(self,
            attr_cls: StandardAttribute,
            add_to_method: bool,
            position: dict = None,
            optional: bool = False,
            alt: str = None,
            default_value: str = None,
            name: str = None,
            overwrite: bool = False
            ):
        """Add a standard attribute to a HDF5 object File"""

        self.convention._add(attr_cls=attr_cls,
                             target_cls=self.cls,
                             target_property=self.prop,
                             method=self.method,
                             add_to_method=add_to_method,
                             position=position,
                             optional=optional,
                             alt=alt,
                             default_value=default_value,
                             name=name,
                             overwrite=overwrite)


# class __Convention(_Convention):
#     """A convention is a set of standard attributes that are used to describe the data in a file."""
#
#     @property
#     def File(self) -> H5ObjConventionInterface:
#         """File as the target class is passed the the HDF5 Object Convention Interface class"""
#         from ..wrapper.core import File
#         return H5ObjConventionInterface(self, cls=File)
#
#     @property
#     def Dataset(self) -> H5ObjConventionInterface:
#         """Dataset as the target class is passed the the HDF5 Object Convention Interface class"""
#         from ..wrapper.core import Dataset
#         return H5ObjConventionInterface(self, cls=Dataset)
#
#     @property
#     def Group(self) -> H5ObjConventionInterface:
#         """Group as the target class is passed the the HDF5 Object Convention Interface class"""
#         from ..wrapper.core import Group
#         return H5ObjConventionInterface(self, cls=Group)


def use(convention_name: Union[str, Convention]) -> None:
    """Use a convention by name"""
    if isinstance(convention_name, Convention):
        convention_name = convention_name.name
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
__all__ = ['datetime_str', 'set_loglevel', 'StandardAttribute']


def from_yaml(yaml_filename: Union[str, pathlib.Path],
              register: bool = True) -> List[StandardAttribute]:
    """Read convention from from a yaml file

    Parameters
    ----------
    yaml_filename: Union[str, pathlib.Path]
        Path to yaml file
    register:
        Whether to register the convention for direct use. Default is True

    Returns
    -------
    cv: Convention
        The convention object
    """
    yaml_filename = pathlib.Path(yaml_filename)
    with open(yaml_filename, 'r') as f:
        attrs = yaml.safe_load(f)
    std_attrs = [StandardAttribute(name, **values) for name, values in attrs.items() if isinstance(values, dict)]
    meta = {name: value for name, value in attrs.items() if not isinstance(value, dict)}
    if 'name' not in meta:
        meta['name'] = yaml_filename.stem
    meta = {name.strip('_'): value for name, value in meta.items()}
    cv = Convention(**meta)
    for s in std_attrs:
        cv.add(s)
    if register:
        cv.register()
    return cv


def from_zenodo(doi, name=None):
    """Download a YAML file from a zenodo repository"""
    return from_yaml(download_zenodo_file(doi, name))
