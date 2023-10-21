import copy
import inspect
import pathlib
import re
import shutil
import sys
from pydoc import locate
from typing import Union, List, Dict

import forge
import yaml
import zenodo_search as zsearch

from . import cfg
from . import errors
from . import logger
from .standard_attributes import StandardAttribute, __doc_string_parser__
from .._repr import make_italic, make_bold
from .._user import UserDir
from .standard_names import cache

CV_DIR = UserDir['conventions']


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
    decoders: List[str], optional=None
        List of decoders to be used for decoding datasets. If None, no decoder is used.
        Decoders can be written by the user and registered with `h5tbx.register_dataset_decoder(<decoder_func>)`.
    """

    def __init__(self,
                 name: str,
                 contact: str,  # ORCID of researcher
                 institution: str = None,  # only if different than that from contact
                 standard_attributes: dict = None,
                 decoders: Union[str, List[str]] = None,
                 filename=None):
        from ..wrapper.core import File, Group, Dataset

        if decoders is None:
            self._decoders = tuple()
        else:
            if isinstance(decoders, str):
                self._decoders = (decoders,)
            else:
                self._decoders = tuple(decoders)

        # a convention may be stored locally:
        if filename is not None:
            self.filename = pathlib.Path(filename).absolute()
        else:
            self.filename = filename

        self.contact = contact
        self.institution = institution

        self._registered_standard_attributes = {}
        self.name = name

        self.properties = {}
        self.methods = {File: {}, Group: {}, Dataset: {}}

        if standard_attributes is None:
            standard_attributes = {}
        for std_name, std in standard_attributes.items():
            self.add(std)

    def add(self, std_attr: StandardAttribute):
        _registered_names = list(self._registered_standard_attributes.keys())

        # check if the name is already registered:
        _cls = std_attr.target_cls

        std_attr_name = std_attr.name.split('-')[0]
        std_attr.name = std_attr_name

        prop = self.properties.get(_cls, None)
        if prop is not None:
            if std_attr_name in self.properties[_cls]:
                raise errors.ConventionError(f'A standard attribute with the name "{std_attr_name}" '
                                             f'is already registered for "{std_attr.target_cls}".')
        if std_attr.requirements is not None:
            if not all(r in _registered_names for r in std_attr.requirements):
                # collect the missing ones:
                _missing_requirements = []
                for r in std_attr.requirements:
                    if r not in _registered_names:
                        _missing_requirements.append(r)
                raise errors.ConventionError(f'Not all requirements for "{std_attr_name}" are registered. '
                                             f'Please add them to the convention first: {_missing_requirements}')

        self._registered_standard_attributes[std_attr_name] = std_attr

        method_name = std_attr.target_method

        target_cls = std_attr.target_cls

        if target_cls not in self.properties:
            self.properties[target_cls] = {}
        self.properties[target_cls][std_attr_name] = std_attr

        if target_cls not in self.methods:
            self.methods[target_cls] = {}

        add_to_method = True  # for now all standard attributes are always added to the method (signature)
        if add_to_method:
            cls = StandardAttribute.METHOD_CLS_ASSIGNMENT[method_name]
            if method_name not in self.methods[cls]:
                self.methods[cls][method_name] = {}

            self.methods[cls][method_name][std_attr_name] = std_attr

    def delete(self):
        """Delete the convention from the user directory."""
        delete(self.name.lower().replace('-', '_'))

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

    def __enter__(self):
        self._curr_cv = get_current_convention()
        use(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        use(self._curr_cv.name)

    @property
    def registered_standard_attributes(self):
        """Return the registered standard attributes."""
        return self._registered_standard_attributes

    @property
    def decoders(self):
        return self._decoders

    def add_decoder(self, decoder: str):
        """Add a decoder to the convention."""
        if not isinstance(decoder, str):
            raise TypeError(f'Expected a string, got {type(decoder)}')
        from ..wrapper import ds_decoder
        if decoder not in ds_decoder.registered_dataset_decoders:
            raise KeyError(f'The decoder "{decoder}" is not registered.')
        self._decoders += (decoder,)

    def remove_decoder(self, decoder: str):
        decoders = list(self._decoders)
        decoders.remove(decoder)
        self._decoders = tuple(decoders)
        return self._decoders

    @staticmethod
    def from_yaml(yaml_filename, overwrite: bool = False) -> "Convention":
        """Create a convention from a yaml file."""
        return from_yaml(yaml_filename, overwrite=overwrite)

    def pop(self, *names) -> "Convention":
        """removes the standard attribute with the given name from the convention

        Parameters
        ----------
        name: str
            name of the standard attribute to remove

        Returns
        -------
        Convention
            a new convention without the given standard attribute
        """
        new_conv = copy.deepcopy(self)
        for prop in new_conv.properties.values():
            for name in names:
                prop.pop(name, None)

        _new_methods_dict = new_conv.methods
        for cls, meth_dict in new_conv.methods.items():
            for meth_name, std_attr in meth_dict.items():
                for name in names:
                    _new_methods_dict[cls][meth_name].pop(name, None)
        new_conv.methods = _new_methods_dict
        return new_conv

    def _add_signature(self):
        for cls, methods in self.methods.items():
            for method_name, std_attrs in methods.items():
                for std_attr_name, std_attr in std_attrs.items():

                    __doc_string_parser__[cls][method_name].add_additional_parameters(
                        {std_attr_name: {'default': std_attr.default_value,
                                         'type': std_attr.type_hint,
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

                    type_hint = locate(std_attr.type_hint)

                    setattr(cls, method_name, forge.insert(forge.arg(f'{std_attr_name}',
                                                                     default=std_attr.default_value,
                                                                     type=type_hint),
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
        add_convention(self)


from .errors import ConventionNotFound


def _import_convention(convention_name) -> "module":
    import importlib
    try:
        return importlib.import_module(f'{convention_name}')
    except ImportError:
        print(f"Failed to import module {convention_name}")


def _get_convention_from_dir(convention_name: str) -> "Convention":
    _convention_name = convention_name.lower().replace('-', '_')
    assert '-' not in _convention_name
    if _convention_name in get_registered_conventions():
        return get_registered_conventions()[convention_name]
    _convention_py_filename = CV_DIR / f'{_convention_name}' / f'{_convention_name}.py'
    if not _convention_py_filename.exists():
        raise ConventionNotFound(f'Convention "{convention_name}" not found.')
    sys.path.insert(0, str(_convention_py_filename.parent))
    # import:
    _import_convention(_convention_name)
    # now it is registered and can be returned:
    return get_registered_conventions()[convention_name]


class use:
    """Set the configuration parameters."""

    def __init__(self, convention_name: Union[str, Convention]):
        self._latest_convention = get_current_convention()
        registered_conventions = get_registered_conventions()
        if convention_name is not None:
            if isinstance(convention_name, Convention):
                convention_name = convention_name.name
            _convention_name = convention_name.lower().replace('-', '_')
            assert '-' not in _convention_name
            if _convention_name not in registered_conventions:
                cv = _get_convention_from_dir(convention_name)
                convention_name = cv.name
        self._current_convention = _use(convention_name)

    def __repr__(self):
        return f'using("{self._current_convention.name}")'

    def __enter__(self):
        return self._current_convention

    def __exit__(self, *args, **kwargs):
        _use(self._latest_convention)


from h5rdmtoolbox.wrapper import ds_decoder


def _use(convention_name: Union[str, Convention]) -> Convention:
    """Use a convention by name"""
    if isinstance(convention_name, Convention):
        convention_name = convention_name.name
    current_convention = get_current_convention()

    if convention_name is None:
        # reset to default convention
        convention_name = 'h5py'

    if convention_name not in get_registered_conventions():
        raise ValueError(f'Convention "{convention_name}" is not registered')

    logger.debug(f'Switching to convention "{convention_name}"')

    if current_convention is not None:
        if convention_name == current_convention.name:
            return current_convention

        # reset signature and dataset decoders:
        current_convention._delete_signature()
    ds_decoder.decoder_names = ()

    # update signature:
    current_convention = get_registered_conventions()[convention_name]
    current_convention._add_signature()

    # update dataset decoders:
    ds_decoder.decoder_names = current_convention.decoders

    set_current_convention(current_convention)

    return current_convention


def get_registered_conventions() -> Dict:
    """Return dictionary of registered conventions"""
    return cfg._registered_conventions


def register_convention(new_convention: Convention) -> None:
    """Return dictionary of registered conventions"""
    if new_convention in cfg._registered_conventions:
        raise ValueError(f'Convention "{new_convention}" is already registered')
    cfg._registered_conventions[new_convention.name] = new_convention


def add_convention(convention, name=None):
    if name is None:
        name = convention.name
    cfg._registered_conventions[name] = convention


def get_current_convention():
    """Return the current convention"""
    return cfg._current_convention


def set_current_convention(convention: Convention):
    cfg._current_convention = convention


datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'
__all__ = ['datetime_str', 'StandardAttribute']


def _process_relpath(rel_filename, relative_to):
    return str((relative_to / rel_filename).absolute())


def _process_paths(data: Union[Dict, str], relative_to) -> Dict:
    # processed_data = {}
    if isinstance(data, str):
        match = re.search(r'relpath\((.*?)\)', data)
        if match:
            return _process_relpath(match.group(1), relative_to)
        return data
    elif isinstance(data, list):
        return [_process_paths(item, relative_to) for item in data]
    elif isinstance(data, dict):
        _data = data.copy()
        for key, value in data.items():
            if isinstance(value, str):
                match = re.search(r'relpath\((.*?)\)', value)
                if match:
                    _data[key] = _process_relpath(match.group(1), relative_to)
            elif isinstance(value, list):
                _data[key] = [_process_paths(item, relative_to) for item in value]
            elif isinstance(value, dict):
                _data[key] = _process_paths(_data[key], relative_to)
        return _data
    return data


def delete(convention_name: str):
    """Delete convention from directory"""
    shutil.rmtree(CV_DIR / convention_name)


def from_yaml(yaml_filename: Union[str, pathlib.Path, List[str], List[pathlib.Path]],
              overwrite: bool = False) -> Convention:
    """Read convention from from a yaml file. A convention YAML file
    requires to have valid standard attribute entries and must contain
    the keys "__name__" and "__contact__".

    Parameters
    ----------
    yaml_filename: Union[str, pathlib.Path]
        Path to yaml file
    overwrite: bool=False
        Overwrite existing convention. If False and convention already exists,
        the existing convention is returned.

    Returns
    -------
    cv: Convention
        The convention object

    Raises
    ------
    ValueError
        If the YAML file does not contain "__name__" or "__contact__"
    """
    if isinstance(yaml_filename, (list, tuple)):
        raise ValueError('Only one YAML file can be specified')

    yaml_filename = pathlib.Path(yaml_filename)

    with open(yaml_filename, 'r') as f:
        attrs = _process_paths(yaml.safe_load(f), relative_to=yaml_filename.parent)

    if '__name__' not in attrs:
        raise ValueError(f'YAML file {yaml_filename} does not contain "__name__". Is the file a valid convention?')
    if '__contact__' not in attrs:
        raise ValueError(f'YAML file {yaml_filename} does not contain "__contact__". Is the file a valid convention?')

    # check if name already exists!
    convention_name = attrs['__name__'].lower().replace('-', '_')
    if convention_name in [d.name for d in CV_DIR.glob('*')]:
        if not overwrite:
            return _get_convention_from_dir(attrs['__name__'])
        # overwriting existing convention
        delete(convention_name)

    from . import generate
    generate.write_convention_module_from_yaml(yaml_filename, name=attrs['__name__'])

    return _get_convention_from_dir(attrs['__name__'])

    # decoders = attrs.pop('__decoders__', None)
    #
    # std_attrs = []
    #
    # standard_attributes = {k: v for k, v in attrs.items() if isinstance(v, dict)}
    #
    # for name, values in standard_attributes.items():
    #     target_methods = values.get('target_methods', None)
    #     if isinstance(target_methods, (tuple, list)):
    #         warnings.warn(f'Convention "{name}" contains a list of target methods. This is not supported anymore. '
    #                       f'Please use a single target method instead.')
    #         for target_methods in target_methods:
    #             _values = values.copy()
    #             _values.pop('target_methods')
    #             _values['target_method'] = target_methods
    #             new_sattr = StandardAttribute(name, **_values)
    #             std_attrs.append(new_sattr)
    #     else:
    #         std_attrs.append(StandardAttribute(name, **values))
    # meta = {name.strip('__'): value for name, value in attrs.items() if isinstance(value, str)}
    # if 'name' not in meta:
    #     meta['name'] = yaml_filename.stem
    # meta = {name.strip('_'): value for name, value in meta.items()}
    # cv = Convention(filename=yaml_filename, decoders=decoders, **meta)
    # for std_attr in std_attrs:
    #     cv.add(std_attr)
    #
    # if register:
    #     cv.register()
    # return cv


def from_zenodo(doi, name=None,
                overwrite: bool = False,
                force_download: bool = False) -> Convention:
    """Download a YAML file from a zenodo repository

    Parameters
    ----------
    doi: str
        DOI of the zenodo repository. Can be a short DOI or a full DOI or the URL (e.g. 8357399 or
        10.5281/zenodo.8357399 or https://doi.org/10.5281/zenodo.8357399)
    overwrite: bool = False
        Whether to overwrite existing convention with the same name. Default is False
    force_download: bool
        Whether to force download the file even if it is already cached. Default is False

    Returns
    -------
    cv: Convention
        The convention object
    """
    # depending on the input, try to convert to a valid DOI:
    # doi = zsearch.utils.parse_doi(doi)
    doi = str(doi)
    if name is None:
        filename = UserDir['cache'] / f'{doi.replace("/", "_")}'
    else:
        filename = UserDir['cache'] / f'{doi.replace("/", "_")}/{name}'

    if not filename.exists() or force_download:
        record = zsearch.search_doi(doi, parse_doi=False)
        if name is None:
            matches = [file for file in record.files if file['filename'].rsplit('.', 1)[-1] == 'yaml']
            if len(matches) == 0:
                raise ValueError(f'No file with suffix ".yaml" found in record {doi}')
        else:
            matches = [file for file in record.files if file['key'] == name]
            if len(matches) == 0:
                raise ValueError(f'No file with name "{name}" found in record {doi}')

        file0 = zsearch.ZenodoFile(matches[0])
        if file0['filename'].rsplit('.', 1)[-1] != 'yaml':
            raise ValueError(f'The file with name "{name}" is not a YAML file')

        _filename = file0.download(destination_dir=filename.parent)
        shutil.move(_filename, filename)

    return from_yaml(filename, overwrite=overwrite)
