""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)
The standard name definitions (name, description, units) are to be provided in XML files. Two xml files
are provided by this sub-packages (fluid and piv). As the project is under development, they are generated
in the fluid.py file but in later versions the conventions will only be provided as xml files.
"""
import forge
import inspect
import pathlib
import re
import shutil
import yaml
import zenodo_search as zsearch
from pydoc import locate
from typing import Union, List

from . import errors
from .layout import Layout, validators
from .layout.validators import Validator
from .standard_attributes import StandardAttribute, __doc_string_parser__
from .._logger import loggers
from .._repr import make_italic, make_bold
from .._user import UserDir

__all__ = ['Layout', 'validators', 'Validator', 'Convention']

logger = loggers['conventions']

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

        if self.use_scale_and_offset:
            scale_attr = StandardAttribute(name=self.scale_attribute_name,
                                           validator='$pintquantity',
                                           target_methods='create_dataset',
                                           description='Scale factor for the dataset values.',
                                           position={'after': 'data'},
                                           return_type='pint.Quantity',
                                           default_value=StandardAttribute.NONE)
            self.add(scale_attr)
            offset_attr = StandardAttribute(name=self.offset_attribute_name,
                                            validator={'$type': (int, float)},
                                            target_methods='create_dataset',
                                            description='Scale factor for the dataset values.',
                                            position={'after': 'data'},
                                            default_value=StandardAttribute.NONE)
            self.add(offset_attr)

            units_attr = StandardAttribute(name='units',
                                           validator='$pintunit',
                                           target_methods='create_dataset',
                                           description='Physical unit of the dataset.',
                                           default_value='$EMPTY',
                                           position={'after': 'data'},
                                           return_type='pint.Unit')
            self.add(units_attr)

    def __repr__(self):
        header = f'Convention("{self.name}")'
        out = f'{make_bold(header)}'
        out += f'\ncontact: {self.contact}'

        for cls, method_standard_attributes in self.methods.items():
            for method_name, standard_attributes in method_standard_attributes.items():
                out += f'\n  {cls.__name__}.{method_name}():'
                if len(standard_attributes) == 0:
                    out += f' ({make_italic("Nothing registered")})'
                    continue
                # if props exist list them. first required, then optional
                prop_dict = {'positional': {}, 'keyword': {}}
                for std_attr_name, std_attr in standard_attributes.items():
                    # for property_name, property_dict in methods.items():
                    if std_attr.is_positional():
                        prop_dict['positional'][std_attr_name] = std_attr
                    else:
                        prop_dict['keyword'][std_attr_name] = std_attr

                for k, v in prop_dict['positional'].items():
                    out += f'\n    * {make_bold(k)}:\n\t\t' \
                           f'{v.description}'
                for k, v in prop_dict['keyword'].items():
                    default_value = v.default_value
                    if default_value == StandardAttribute.NONE:
                        default_value = 'None'

                    out += f'\n    * {make_italic(k)} (default={default_value}):\n\t\t' \
                           f'{v.description}'
        out += '\n'
        return out

    def __getitem__(self, std_name) -> StandardAttribute:
        return self._registered_standard_attributes[std_name]

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

        assert isinstance(std_attr.target_methods, tuple)
        assert isinstance(std_attr.target_cls, tuple)

        for method_name, target_cls in zip(std_attr.target_methods, std_attr.target_cls):

            target_cls = StandardAttribute.PROPERTY_CLS_ASSIGNMENT[method_name]
            if target_cls not in self.properties:
                self.properties[target_cls] = {}
            self.properties[target_cls][std_attr.name] = std_attr

            if target_cls not in self.methods:
                self.methods[target_cls] = {}

            add_to_method = True  # for now all standard attributes are always added to the method (signature)
            if add_to_method:
                cls = StandardAttribute.METHOD_CLS_ASSIGNMENT[method_name]
                if method_name not in cls.__dict__:
                    raise AttributeError(
                        f'Cannot add standard attribute {std_attr.name} to method {method_name} of {target_cls} '
                        'because it does not exist.'
                    )
                if method_name not in self.methods[cls]:
                    self.methods[cls][method_name] = {}

                self.methods[cls][method_name][std_attr.name] = std_attr

    def _add_signature(self):
        for cls, methods in self.methods.items():
            for method_name, std_attrs in methods.items():
                for std_attr_name, std_attr in std_attrs.items():

                    __doc_string_parser__[cls][method_name].add_additional_parameters(
                        {std_attr_name: {'default': std_attr.default_value,
                                         'type': std_attr.input_type,
                                         'description': std_attr.description}}
                    )

                    if isinstance(std_attr.position, dict):
                        position = std_attr.position
                    else:
                        signature = inspect.signature(cls.__dict__[method_name])
                        if std_attr.is_positional():
                            params = [param for param in signature.parameters.values() if
                                      param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
                            position = {'after': params[-1].name}
                        else:
                            params = [param for param in signature.parameters.values() if
                                      param.kind == inspect.Parameter.KEYWORD_ONLY]
                            if len(params) == 0:
                                params = [param for param in signature.parameters.values() if
                                          param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
                            position = {'after': params[-1].name}

                    input_type = locate(std_attr.input_type)

                    setattr(cls, method_name, forge.insert(forge.arg(f'{std_attr_name}',
                                                                     default=std_attr.default_value,
                                                                     type=input_type),
                                                           **position)(cls.__dict__[method_name]))
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


class use:
    """Set the configuration parameters."""

    def __init__(self, convention_name: Union[str, Convention]):
        self._current_convention = current_convention
        _use(convention_name)

    def __enter__(self):
        return

    def __exit__(self, *args, **kwargs):
        _use(self._current_convention)


def _use(convention_name: Union[str, Convention]) -> None:
    """Use a convention by name"""
    if isinstance(convention_name, Convention):
        convention_name = convention_name.name
    global current_convention
    if convention_name is None:
        convention_name = 'h5py'
    if convention_name not in registered_conventions:
        raise ValueError(f'Convention "{convention_name}" is not registered')
    logger.debug(f'Switching to convention "{convention_name}"')
    if current_convention is not None:
        if convention_name == current_convention.name:
            return  # nothing to do
        current_convention._delete_signature()
    current_convention = registered_conventions[convention_name]
    current_convention._add_signature()


current_convention: Union[None, Convention] = None

datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'
__all__ = ['datetime_str', 'StandardAttribute']


def from_yaml(yaml_filename: Union[str, pathlib.Path],
              register: bool = True) -> List[StandardAttribute]:
    """Read convention from from a yaml file. A convention YAML file
    requires to have valid standard attribute entries and must contain
    the keys "__name__" and "__contact__".

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

    Raises
    ------
    ValueError
        If the YAML file does not contain "__name__" or "__contact__"
    """
    yaml_filename = pathlib.Path(yaml_filename)
    with open(yaml_filename, 'r') as f:
        attrs = yaml.safe_load(f)

    if '__name__' not in attrs:
        raise ValueError(f'YAML file {yaml_filename} does not contain "__name__". Is the file a valid convention?')
    if '__contact__' not in attrs:
        raise ValueError(f'YAML file {yaml_filename} does not contain "__contact__". Is the file a valid convention?')

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
    # depending on the input, try to convert to a valid DOI:
    if isinstance(doi, int):
        doi = f'10.5281/zenodo.{doi}'
    elif isinstance(doi, str):
        if doi.startswith('https://zenodo.org/record/'):
            doi = doi.replace('https://zenodo.org/record/', '10.5281/zenodo.')
        elif bool(re.match(r'^\d+$', doi)):
            # pure numbers:
            doi = f'10.5281/zenodo.{doi}'
    else:
        raise TypeError(f'Invalid type for DOI: {doi}. Expected int or str')

    if not bool(re.match(r'^10\.5281/zenodo\.\d+$', doi)):
        raise ValueError(f'Invalid DOI pattern: {doi}. Expected format: 10.5281/zenodo.<number>')

    filename = UserDir['cache'] / f'{doi.replace("/", "_")}/{name}'
    if not filename.exists():
        record = zsearch.search(doi)[0]
        for file in record.files:
            if file['key'] == name:
                assert file.type == 'yaml'
                _filename = file.download(destination=filename.parent)
                shutil.move(_filename, filename)
                break
    return from_yaml(filename)
