import abc
import copy
import forge
import h5py
import inspect
import logging
import pathlib
import re
import shutil
import sys
import warnings
import yaml
from pydoc import locate
from typing import Union, List, Dict, Tuple, Any

from h5rdmtoolbox import errors
from h5rdmtoolbox.repository import RepositoryInterface
from h5rdmtoolbox.wrapper import ds_decoder
from . import cfg
from . import consts
from . import errors
from .errors import ConventionNotFound
from .standard_attributes import StandardAttribute, __doc_string_parser__
from .utils import json2yaml
from .._repr import make_italic, make_bold
from ..user import UserDir
from ..repository import zenodo
from ..repository.zenodo.utils import recid_from_doi_or_redid

logger = logging.getLogger('h5rdmtoolbox')
CV_DIR = UserDir['convention']

datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'


class MissingAttribute:

    def __init__(self,
                 object_name: str,
                 attribute_name: str):
        self.object_name = object_name
        self.attribute_name = attribute_name

    def __str__(self):
        return f'Attribute "{self.attribute_name}" is missing in "{self.object_name}".'

    def __repr__(self):
        return f'MissingAttribute({self.object_name}, {self.attribute_name})'


class InvalidAttribute:
    def __init__(self,
                 object_name: str,
                 attribute_name: str,
                 attribute_value: Any,
                 error_message: str):
        self.object_name = object_name
        self.attribute_name = attribute_name
        self.attribute_value = attribute_value
        self.error_message = error_message

    def __str__(self):
        return f'Attribute "{self.attribute_name}" in "{self.object_name}" has an invalid value ' \
               f'"{self.attribute_value}". Error message: "{self.error_message}"'

    def __repr__(self):
        return f'InvalidAttribute({self.object_name}, {self.attribute_name}, {self.attribute_value}, {self.error_message})'


class AbstractConvention(abc.ABC):
    """Abstract class definition for convention"""

    # Class interfaces:
    # Reader interfaces:
    @classmethod
    @abc.abstractmethod
    def from_yaml(cls, filename: Union[str, pathlib.Path]):
        """read a convention from a YAML file"""

    @classmethod
    @abc.abstractmethod
    def from_json(cls, filename: Union[str, pathlib.Path]):
        """read a convention from a JSON file"""

    # Validater:
    @abc.abstractmethod
    def validate(self, file_or_filename: Union["h5tbx.File", h5py.File, str, pathlib.Path]) -> List[Dict]:
        """Checking a file for compliance with the convention. Shall return dictionary indicating
        invalid attributes."""


class Convention(AbstractConvention):
    """Convention class

    A convention is a set of standard attributes, which are defined in a YAML or JSON file.
    Recommended initialization is via `Convention.from_yaml(<yaml_filename>)` or
    `Convention.from_json(<json_filename>)`.

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
                 *,  # enforce keyword arguments
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
            self.add_standard_attribute(std)

    def add_standard_attribute(self, std_attr: StandardAttribute) -> None:
        """Add a standard attribute to the convention."""
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

    def add(self, std_attr: StandardAttribute) -> None:
        """Add a standard attribute to the convention."""
        warnings.warn('The method "add" is deprecated. Please use "add_standard_attribute" instead.',
                      DeprecationWarning)
        return self.add_standard_attribute(std_attr)

    def delete(self):
        """Delete the convention from the user directory."""
        delete(self.name.lower().replace('-', '_'))

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.name}")'

    def __str__(self):
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
                    out += f'\n    * {make_bold(k + " (obligatory)")} :\n\t\t' \
                           f'{v.description}'
                for k, v in prop_dict['keyword'].items():
                    default_value = v.default_value
                    if default_value == StandardAttribute.NONE:
                        out += f'\n    * {make_italic(k)}:\n\t\t' \
                               f'{v.description}'
                    else:
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
    def decoders(self) -> Tuple[str]:
        """Return registered decoders."""
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
        """Remove a decoder from the convention.

        Parameters
        ----------
        decoder: str
            name of the decoder to remove. TODO: Check if decoder is registered.
        """
        decoders = list(self._decoders)
        decoders.remove(decoder)
        self._decoders = tuple(decoders)
        return self._decoders

    @classmethod
    def from_json(cls, json_filename: Union[str, pathlib.Path], overwrite: bool = False) -> "Convention":
        """Create a convention from a json file."""
        return cls.from_yaml(json2yaml(json_filename), overwrite=overwrite)

    @classmethod
    def from_yaml(cls, yaml_filename: Union[str, pathlib.Path], overwrite: bool = False):
        """Create a convention from a yaml file.
        The YAML file must have the following structure:

        # file content:
        __name__ = "name of the convention"
        __contact__ = "contact email or orcid or ..."
        __version__ = "version of the convention"

        <standard_attribute_name>:
            target_cls: <class name>
            target_method: <method name>
            description: <description>
            default_value: <default value> # optional, default is "$None"
            requirements: [<list of required standard attributes>] # optional
        # end of file

        Note, that the name, author and version are required with the double underscores because they
        need to be distinguished from the standard attributes. E.g. "contact" could be a standard attribute.

        Parameters
        ----------
        yaml_filename: str
            path to the yaml file
        overwrite: bool
            if True, overwrite an existing (registered) convention with the same name

        Returns
        -------
        Convention
            The created conventionRaises

        Raises
        ------
        ValueError
            If the YAML file does not contain "__name__" or "__contact__"
        """
        if not isinstance(yaml_filename, (str, pathlib.Path)):
            raise TypeError('Parameter yaml_filename must be a filename, i.e. str or pathlib.Path, '
                            f'got {type(yaml_filename)}')

        yaml_filename = pathlib.Path(yaml_filename)

        with open(yaml_filename, 'r') as f:
            attrs = _process_paths(yaml.safe_load(f), relative_to=yaml_filename.parent)

        if '__name__' not in attrs:
            raise ValueError(f'YAML file {yaml_filename} does not contain "__name__". Is the file a valid convention?')
        if '__contact__' not in attrs:
            raise ValueError(
                f'YAML file {yaml_filename} does not contain "__contact__". Is the file a valid convention?')

        # check if name already exists!
        convention_name = attrs['__name__'].lower().replace('-', '_')
        if convention_name in [d.name for d in CV_DIR.glob('*')]:
            if not overwrite:
                return _get_convention_from_dir(attrs['__name__'])
            # overwriting existing convention
            delete(convention_name)
            logger.debug(f'Convention exists and overwrite is True: Deleting convention "{convention_name}"')

        from . import generate
        generate.write_convention_module_from_yaml(yaml_filename, name=attrs['__name__'])

        # add_convention(yaml_filename, name=attrs['__name__'])
        # assert attrs['__name__'] in get_registered_conventions()
        return _get_convention_from_dir(attrs['__name__'])

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
                    try:  # try it. If a convention is created during runtime, this may happen!
                        setattr(cls, name, forge.delete(f'{prop_name}')(cls.__dict__[name]))
                    except ValueError:
                        pass
                    __doc_string_parser__[cls][name].restore_docstring()
                    # orig_docs[cls][name]['callable'].__doc__ = orig_docs[cls][name]['doc']

    def register(self):
        """Register the convention in the convention directory"""
        add_convention(self)

    def validate(self, file_or_filename: Union[str, pathlib.Path, "File"]) -> List[Dict]:
        """Checks a file for compliance with the convention. It will NOT raise an error but
        return a list of invalid attributes.

        Parameters
        ----------
        file_or_filename: str, pathlib.Path, File
            path to the file or a File (h5tbx.File!) object

        Returns
        -------
        List[Dict]
            The invalid attributes
        """
        from ..wrapper.core import File
        if not isinstance(file_or_filename, (str, pathlib.Path)):
            with File(file_or_filename, 'r') as f:
                return self.check(f)
        failed = []

        convention = self

        def _is_str_dataset(node):
            if node.dtype.kind == 'S':
                return True
            return False

        def _validate_convention(name, node):
            """Checks if the node (dataset or group) is compliant with the convention"""
            for k, v in convention.properties.items():
                if isinstance(node, k):
                    for ak, av in v.items():
                        if av.default_value is not consts.DefaultValue.EMPTY:
                            if ak in node.attrs:
                                try:
                                    node.attrs[ak]
                                except errors.StandardAttributeError as e:
                                    failed.append(dict(name=node.name, attr_name=ak, attr_value=node.attrs.raw[ak],
                                                       reason='invalid_value',
                                                       error_message=str(e)))
                        else:  # av.default_value is consts.DefaultValue.EMPTY:
                            if av.target_method == 'create_string_dataset' and not _is_str_dataset(node):
                                continue  # not the responsibility of this validator
                            if av.target_method == 'create_dataset' and _is_str_dataset(node):
                                continue  # not the responsibility of this validator

                            if ak not in node.attrs:
                                logger.debug(
                                    f'The attribute "{ak}" is missing in the dataset "{name}" but '
                                    'is required by the convention')
                                failed.append(MissingAttribute(object_name=node.name,
                                                               attribute_name=ak))
                            else:
                                # just by accessing the standard attribute, the validation is performed
                                try:
                                    _ = node.attrs[ak]
                                    # av.validate(value_to_check, parent=node, attrs=node.attrs.raw)
                                    logger.debug(f'The attribute "{ak}" is valid')
                                except errors.StandardAttributeError as e:
                                    logger.debug(f'The attribute "{ak}" exists but is invalid')
                                    failed.append(InvalidAttribute(object_name=node.name,
                                                                   attribute_name=ak,
                                                                   attribute_value=node.attrs.raw[ak],
                                                                   error_message=str(e)))

        with File(file_or_filename, 'r') as f:
            logger.debug(f'Checking file {file_or_filename} for compliance with convention {self.name}')
            _validate_convention('/', f)
            f.visititems(_validate_convention)

        return failed


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
    cv = get_registered_conventions()[convention_name]
    cv.filename = _convention_py_filename
    return cv


class use:
    """Enable a convention.
    To disable the convention, active an empty convention like so: cv.use(None)

    Parameters
    ----------
    convention_or_name: Union[str, Convention, None]
        The convention name or object to enable.
    """

    def __init__(self, convention_or_name: Union[str, Convention, None]):
        self._latest_convention = get_current_convention()
        registered_conventions = get_registered_conventions()
        if convention_or_name is None:
            self._current_convention = _use(None)
        else:
            if isinstance(convention_or_name, Convention):
                convention_name = convention_or_name.name
            else:
                convention_name = convention_or_name
            _convention_name = convention_name.lower().replace('-', '_')
            assert '-' not in _convention_name
            registered_convention_names = [n.lower().replace('-', '_') for n in registered_conventions]
            if _convention_name not in registered_convention_names:
                cv = _get_convention_from_dir(convention_name)
                convention_name = cv.name
            self._current_convention = _use(convention_name)

    def __repr__(self):
        return f'using("{self._current_convention.name}")'

    def __enter__(self):
        return self._current_convention

    def __exit__(self, *args, **kwargs):
        _use(self._latest_convention)


def _use(convention_or_name: Union[str, Convention, None]) -> Convention:
    """Use a convention by name or Convention object"""
    if isinstance(convention_or_name, Convention):
        convention_name = convention_or_name.name
    else:
        convention_name = convention_or_name
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

    # set_current_convention(current_convention)
    cfg._current_convention = current_convention
    return current_convention


def get_registered_conventions() -> Dict:
    """Return dictionary of registered convention"""
    return cfg._registered_conventions


# unused:
# def register_convention(new_convention: Convention) -> None:
#     """Return dictionary of registered convention"""
#     if new_convention in cfg._registered_conventions:
#         raise ValueError(f'Convention "{new_convention}" is already registered')
#     cfg._registered_conventions[new_convention.name] = new_convention


def add_convention(convention: Convention, name=None):
    """Add a convention to the list of registered convention"""
    if not isinstance(convention, Convention):
        raise ValueError(f'Convention "{convention}" is not a valid convention')
    if name is None:
        name = convention.name
    cfg._registered_conventions[name] = convention


def get_current_convention() -> Union[None, Convention]:
    """Return the current convention"""
    return cfg._current_convention


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


def delete(convention: Union[str, Convention]):
    """Delete convention from directory"""
    if isinstance(convention, Convention):
        convention_name = convention.name
    else:
        convention_name = convention
    cv_dir = CV_DIR / convention_name
    if cv_dir.exists():
        shutil.rmtree(CV_DIR / convention_name)
    cfg._registered_conventions.pop(convention_name, None)
    if convention_name in sys.modules:
        # if the convention (py script) already has been imported, remove it from the list of imported modules:
        del sys.modules[convention_name]


def from_file(filename) -> Convention:
    """Load a convention from a file. Currently yaml and json files are supported"""
    if filename.suffix == '.yaml':
        return from_yaml(filename)
    elif filename.suffix == '.json':
        return from_json(filename)
    else:
        raise ValueError(f'File {filename} has an unknown suffix')


def from_yaml(filename: Union[str, pathlib.Path], overwrite: bool = False) -> Convention:
    """Load a convention from a YAML file. See Convention.from_yaml() for details"""
    return Convention.from_yaml(filename, overwrite=overwrite)


def from_json(filename: Union[str, pathlib.Path], overwrite: bool = False) -> Convention:
    """Load a convention from a JSON file. See Convention.from_json() for details"""
    return Convention.from_json(filename, overwrite=overwrite)


def from_repo(repo_interface: RepositoryInterface,
              name: str,
              take_existing: bool = True,
              force_download: bool = False):
    """Download a YAML file from a repository"""
    # check if file exists:
    # path_compatible_doi = repo_interface.get_doi().replace('/', '_')
    # estimated_filename = UserDir['cache'] / f'{path_compatible_doi}' / name
    # estimated_filename.parent.mkdir(parents=True, exist_ok=True)
    # if estimated_filename.exists():
    #     if not take_existing:
    #         raise FileExistsError(f'File {name} exists in cache but take_existing is set to False.')
    #     if take_existing and not force_download:
    #         return from_file(estimated_filename)

    filename = repo_interface.download_file(name)
    # if estimated_filename.exists():
    #     estimated_filename.unlink()
    # filename.rename(estimated_filename)
    return from_file(filename)


def from_zenodo(doi_or_recid: str,
                name: str = None,
                overwrite: bool = False,
                force_download: bool = False) -> Convention:
    """Download a YAML file from a zenodo repository

    Depreciated. Use `from_repo` in future.

    Parameters
    ----------
    doi_or_recid: str
        DOI of the zenodo repository. Can be a short DOI or a full DOI or the URL (e.g. 10428822 or
        10.5281/zenodo.10428822 or https://doi.org/10.5281/zenodo.10428822 or only the record id, e.g. 10428822)
    name: str=None
        Name to be sed for the filename. If None, the name is taken from the zenodo record.
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
    # parse record id:
    warnings.warn('Please use `from_repo` instead of from_zenodo', DeprecationWarning)
    rec_id = recid_from_doi_or_redid(doi_or_recid)

    if name is None:
        filename = UserDir['cache'] / f'{rec_id}'
    else:
        filename = UserDir['cache'] / f'{rec_id}/{name}'

    if not filename.exists() or force_download:
        record = zenodo.ZenodoRecord(rec_id)

        filenames = list(record.files.keys())

        if name is None:
            yaml_matches = [file for file in filenames if pathlib.Path(file).suffix == '.yaml']
            vfuns_matches = [file for file in filenames if file.endswith('vfuncs.py')]
        else:
            yaml_matches = [file for file in filenames if file == name]
            vfuns_matches = [file for file in filenames if file == f'{name}_vfuncs.py']
            if len(yaml_matches) == 0:
                raise ValueError(f'No file with name "{name}" found in record {doi_or_recid}')

        found_filenames = [f for f in yaml_matches]
        found_filenames.extend(vfuns_matches)
        for match in found_filenames:
            _filename = record.download_file(match, target_folder=pathlib.Path(match).parent)
            shutil.move(_filename, match)

    return from_yaml(yaml_matches[0], overwrite=overwrite)


def yaml2jsonld(yaml_filename: Union[str, pathlib.Path],
                file_url: str = None,
                jsonld_filename: Union[str, pathlib.Path] = None) -> pathlib.Path:
    """Converts a convention stored in a YAML file to JSON-LD"""
    yaml_filename = pathlib.Path(yaml_filename)
    if jsonld_filename is None:
        jsonld_filename = yaml_filename.with_suffix('.jsonld')
    else:
        jsonld_filename = pathlib.Path(jsonld_filename)

    cv = Convention.from_yaml(yaml_filename)

    from rdflib.namespace import DCAT, RDF, DCTERMS, PROV, FOAF
    from ontolutils import M4I
    from rdflib import Graph
    import rdflib
    person_orcid_id = cv.contact  # m4i

    g = Graph()
    if file_url is None:
        n_ds = rdflib.BNode()
    else:
        n_ds = rdflib.URIRef(file_url)
    g.add((n_ds, RDF.type, DCAT.Dataset))

    n_person = rdflib.URIRef(value=person_orcid_id)
    n_affiliation = rdflib.URIRef(value=cv.institution)

    g.add((n_person, RDF.type, FOAF.Person))
    g.add((n_affiliation, RDF.type, PROV.Organization))

    g.add((n_person, M4I.orcidId, rdflib.URIRef(person_orcid_id)))
    g.add((n_person, PROV.hadRole, M4I.Researcher))
    g.add((n_person, PROV.hadRole, M4I.ContactPerson))
    g.add((n_person, rdflib.URIRef("https://schema.org/affiliation"), n_affiliation))

    g.add((n_ds, DCTERMS.creator, n_person))

    # as jsonld:
    with open(jsonld_filename, 'w', encoding='utf-8') as f:
        f.write(g.serialize(format='json-ld',
                            indent=4,
                            context={'dcat': DCAT._NS,
                                     'dcterms': DCTERMS._NS,
                                     'm4i': M4I._NS},
                            compact=False))
    return jsonld_filename


__all__ = ['datetime_str', 'StandardAttribute', "Convention"]
