"""utilities of the h5rdmtoolbox"""
import appdirs
import datetime
import h5py
import hashlib
import json
import logging
import numpy as np
import os
import pathlib
import pint
import re
import requests
import warnings
from h5py import File
from logging.handlers import RotatingFileHandler
from re import sub as re_sub
from typing import Dict, Union, Callable, List, Tuple

from . import _user, get_config
from . import get_ureg
from ._version import __version__

DEFAULT_LOGGING_LEVEL = logging.INFO


class ToolboxLogger(logging.Logger):
    """Wrapper class for logging.Logger to add a setLevel method"""

    def __init__(self, name, level=logging.NOTSET, directory=None):
        super().__init__(name, level)
        self._directory = directory

    def setLevel(self, level):
        """change the log level which displays on the console"""
        old_level = self.handlers[1].level
        self.handlers[1].setLevel(level)


def create_tbx_logger(name, logdir=None) -> ToolboxLogger:
    """Create logger based on name"""
    if logdir is None:
        _logdir = pathlib.Path(appdirs.user_log_dir('h5rdmtoolbox'))
    else:
        _logdir = pathlib.Path(logdir)

    _logdir.mkdir(parents=True, exist_ok=True)

    _logger = ToolboxLogger(logging.getLogger(name), directory=_logdir)

    _formatter = logging.Formatter(
        '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d_%H:%M:%S')

    _file_handler = RotatingFileHandler(_logdir / f'{name}.log')
    _file_handler.setLevel(logging.DEBUG)  # log everything to file!
    _file_handler.setFormatter(_formatter)

    _stream_handler = logging.StreamHandler()
    _stream_handler.setLevel(DEFAULT_LOGGING_LEVEL)
    _stream_handler.setFormatter(_formatter)

    _logger.addHandler(_file_handler)
    _logger.addHandler(_stream_handler)

    return _logger


def get_filesize(path: Union[str, pathlib.Path]) -> int:
    """Get the size of a file in bytes"""
    return os.path.getsize(path) * get_ureg().byte


def has_internet_connection(timeout: int = 5) -> bool:
    """Figure out whether there's an internet connection"""
    try:
        requests.get('https://git.scc.kit.edu', timeout=timeout)
        return True
    except (requests.ConnectionError,
            requests.Timeout):
        return False


def download_file(url, known_hash):
    """Download a file from a URL and check its hash"""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        content = response.content

        # Calculate the hash of the downloaded content
        calculated_hash = hashlib.sha256(content).hexdigest()
        if known_hash:
            if not calculated_hash == known_hash:
                raise ValueError('File does not match the expected has')
        else:
            warnings.warn('No has given!')

        # Save the content to a file
        fname = generate_temporary_filename()
        with open(fname, "wb") as f:
            f.write(content)

        return fname
    raise RuntimeError(f'Failed to download the file from {url}')


def is_xml_file(filename):
    """Check if file is an xml file"""
    with open(filename, 'rb') as file:
        bcontent = file.read()
        content = bcontent.decode('utf-8')
        return re.match(r'^\s*<\?xml', content) is not None


def has_datasets(target: Union[h5py.Group, pathlib.Path]) -> bool:
    """Check if file has datasets"""
    if not isinstance(target, h5py.Group):
        with h5py.File(target) as h5:
            return has_datasets(h5)
    for obj in target.values():
        if isinstance(obj, h5py.Dataset):
            return True
    return False


def has_groups(target: Union[h5py.Group, pathlib.Path]) -> bool:
    """Check if file has groups"""
    if not isinstance(target, h5py.Group):
        with h5py.File(target) as h5:
            return has_groups(h5)
    for obj in target.values():
        if isinstance(obj, h5py.Group):
            return True
    return False


def remove_special_chars(input_string, keep_special='/_', replace_spaces='_'):
    """Generally removes all characters that are no number
    or letter. Per default, underscores and forward slashes
    are kept and spaces are replaced with underscores.

    Typically, used to clean up dataset names that contain special
    characters or spaces which are not allowed for usage in
    natural naming. For this matter, spaces are not allowed in the
    name and should be replaced.

    Parameters
    ----------
    input_string : str
        String with special characters to be removed
    keep_special : str, optional
        Specifies which special characters to keep. Put them
        in one single string. Default is '/_'
    replace_spaces : string, optional
        The string that replaces spaces in the input string.
        Default is '_'. If no action wanted, put False

    Returns
    -------
    _cleaned_str : str
        Processed string without special characters and replaced
        spaces.
    """
    if keep_special:
        _cleaned_str = re_sub('[^a-zA-Z0-9%s ]' % keep_special, '', input_string)
    else:
        _cleaned_str = re_sub('[^a-zA-Z0-9 ]', '', input_string)
    if replace_spaces:
        return _cleaned_str.replace(' ', replace_spaces)
    return _cleaned_str


def generate_temporary_filename(prefix='tmp', suffix: str = '', touch: bool = False) -> pathlib.Path:
    """generates a temporary filename in user tmp file directory

    Parameters
    ----------
    prefix: str, optional='tmp'
        prefix string to put in front of name
    suffix: str, optional=''
        suffix (including '.')
    touch: bool, optional=False
        If True, the empty file is created

    Returns
    -------
    tmp_filename: pathlib.Path
        The generated temporary filename
    """
    _filename = _user.UserDir['tmp'] / f"{prefix}{next(_user._filecounter)}{suffix}"
    while _filename.exists():
        _filename = _user.UserDir['tmp'] / f"{prefix}{next(_user._filecounter)}{suffix}"
    if touch:
        with h5py.File(_filename, 'w'):
            pass
    return _filename


def generate_temporary_directory(prefix='tmp') -> pathlib.Path:
    """generates a temporary directory in user tmp file directory

    Parameters
    ----------
    prefix: str, optional='tmp'
        prefix string to put in front of name

    Returns
    -------
    tmp_filename: pathlib.Path
        The generated temporary filename
    """
    _dir = _user.UserDir['tmp'] / f"{prefix}{next(_user._dircounter)}"
    while _dir.exists():
        _dir = _user.UserDir['tmp'] / f"{prefix}{next(_user._dircounter)}"
    _dir.mkdir(parents=True)
    return _dir


def touch_tmp_hdf5_file(touch=True, attrs=None) -> pathlib.Path:
    """
    Generates a file path in directory h5rdmtoolbox/.tmp
    with filename dsXXXX.hdf where XXXX is more or less a
    random number leading to a unique filename in the tmp
    location. The file is created and the file path is returned

    Returns
    --------
    hdf_filepath: pathlib.Path
        file path to created hdf5 file
    touch : bool, optional=True
        touches the file

    """
    hdf_filepath = generate_temporary_filename(suffix='.hdf')
    if touch:
        with File(hdf_filepath, "w") as h5touch:
            h5touch.attrs['__h5rdmtoolbox_version__'] = __version__
            if attrs is not None:
                for ak, av in attrs.items():
                    create_special_attribute(h5touch.attrs, ak, av)
    return hdf_filepath


def try_making_serializable(d: Dict) -> Dict:
    """Tries to make a dictionary serializable by converting numpy arrays to lists"""
    result_dict = {}
    if not isinstance(d, dict):
        return d
    for key, value in d.items():
        if isinstance(value, dict):
            result_dict[key] = try_making_serializable(value)
        elif isinstance(value, np.ndarray):
            result_dict[key] = value.tolist()
        elif isinstance(value, (int, str, float, bool)):
            result_dict[key] = value
        elif isinstance(value, tuple):
            result_dict[key] = tuple([try_making_serializable(v) for v in value])
        elif isinstance(value, list):
            result_dict[key] = [try_making_serializable(v) for v in value]
        else:
            try:
                result_dict[key] = value.__to_h5attr__()
            except AttributeError:
                warnings.warn(f"Type {type(value)} of value {value} not supported. Maybe json can handle it?")
                result_dict[key] = value
    return result_dict


def create_special_attribute(h5obj: h5py.AttributeManager,
                             name: str,
                             value):
    """Allows writing more than the usual hdf5 attributes"""
    if isinstance(value, dict):
        # some value might be changed to a string first, like h5py objects
        for k, v in value.items():
            if isinstance(v, (h5py.Dataset, h5py.Group)):
                value[k] = v.name
        _value = json.dumps(try_making_serializable(value))
    elif isinstance(value, (h5py.Dataset, h5py.Group)):
        _value = value.name
    elif isinstance(value, str):
        _value = value
    elif isinstance(value, pint.Quantity):
        _value = str(value)
    elif isinstance(value, pathlib.Path):
        _value = str(value)
    elif isinstance(value, datetime.datetime):
        _value = value.strftime(get_config('dtime_fmt'))
    else:
        _value = value

    # parse name as well, it could be an identifier (URI or IRI):
    if hasattr(name, 'fragment'):
        fragment = name.fragment
        if not fragment:
            raise ValueError(f'Name {name} has no fragment')
        from h5rdmtoolbox.wrapper.iri import set_predicate
        set_predicate(h5obj, fragment, name)
        name = fragment

    try:
        h5obj.create(name, data=_value)
    except TypeError:
        try:
            h5obj.create(name, data=str(_value))
        except TypeError as e2:
            raise RuntimeError(f'Error setting attribute to HDF object {h5obj._parent}:'
                               f'\n  name: {name}\n  value: {value} \n  type: {type(value)}\n'
                               f'Original error: {e2}') from e2


def parse_object_for_attribute_setting(value) -> Union[str, int, float, bool, List[str], Tuple]:
    """Parses an object to a string for setting an attribute"""
    if isinstance(value, pint.Unit):
        return str(value)
    if isinstance(value, pint.Quantity):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [parse_object_for_attribute_setting(v) for v in value]
    if isinstance(value, tuple):
        return tuple([parse_object_for_attribute_setting(v) for v in value])
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, str):
        return str(value)
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, (h5py.Dataset, h5py.Group)):
        return value.name
    try:
        return str(value)  # try parsing to string
    except TypeError:
        print(type(value))
        raise TypeError(f"Cannot parse type {type(value)} to string")


OBJ_FLT_DICT = {'group': h5py.Group,
                'groups': h5py.Group,
                'dataset': h5py.Dataset,
                'datasets': h5py.Dataset,
                '$group': h5py.Group,
                '$groups': h5py.Group,
                '$dataset': h5py.Dataset,
                '$datasets': h5py.Dataset}


def process_obj_filter_input(objfilter: str) -> Union[h5py.Dataset, h5py.Group, None]:
    """Return the object based on the input string

    Raises
    ------
    ValueError
        If the input string is not in the list of valid strings (see OBJ_FLT_DICT)
    TypeError
        If the input is not a string or a h5py object (h5py.Dataset or h5py.Group)

    Returns
    -------
    h5py.Dataset or h5py.Group or None
        The object to filter for
    """
    if objfilter is None:
        return
    if isinstance(objfilter, str):
        try:
            return OBJ_FLT_DICT[objfilter.lower()]
        except KeyError:
            raise ValueError(f'Expected values for argument objfilter are "dataset" or "group", not "{objfilter}"')
    if not isinstance(objfilter, (h5py.Dataset, h5py.Group)):
        raise TypeError(f'Expected values for argument objfilter are "dataset" or "group", not {type(objfilter)}')
    return objfilter


class DocStringParser:
    """Parses a docstring into abstract, parameters, returns and notes, allowing for additional parameters to be added
    and then reassembled into a new docstring"""

    def __init__(self, cls_or_method: Callable, additional_parameters: Dict = None):
        self._callable = cls_or_method
        self.original_docstring = cls_or_method.__doc__
        self.abstract, self.parameters, self.returns, self.notes = DocStringParser.parse_docstring(
            self.original_docstring
        )
        self.additional_parameters = {}
        if additional_parameters is None:
            additional_parameters = {}
        self.add_additional_parameters(additional_parameters)

    def get_original_doc_string(self):
        """Returns the original docstring"""
        return self.original_docstring

    def get_docstring(self) -> str:
        """Reassembles the docstring from the parsed components"""
        from .convention.standard_attributes import DefaultValue

        new_doc = ''
        if self.abstract:
            for a in self.abstract:
                new_doc += f'{a}\n'
        new_doc += f'\n\nParameters\n----------'
        for k in self.parameters:
            # if k['name'].startswith('**'):
            new_doc += f"\n{k['name']}: {k['type']} = {k['default']}\n\t{k['description']}"

        new_doc += f'\n\nStandard Attributes\n-------------------'
        for ak, av in self.additional_parameters.items():
            if av['default'] == DefaultValue.EMPTY:
                new_doc += f"\n{ak}: {av['type']} \n\t{av['description']}"
            else:
                new_doc += f"\n{ak}: {av['type']} = {av['default']}\n\t{av['description']}"
        new_doc += '\n'

        if self.returns:
            new_doc += f'\n\nReturns\n-------'

            for k in self.returns:
                new_doc += f"\n{k['name']}: {k['type']}\n\t{k['description']}"

        if self.notes:
            new_doc += f'\n\nNotes'
            for n in self.notes:
                new_doc += f'\n{n}'

        return new_doc

    def restore_docstring(self):
        """Restores the original docstring"""
        self._callable.__doc__ = self.original_docstring

    def update_docstring(self) -> None:
        """Updates the docstring of the class, method or function with the new docstring"""
        import h5rdmtoolbox as h5tbx
        if self._callable.__name__ == 'create_dataset':
            h5tbx.Group.__dict__[self._callable.__name__].__doc__ = self.get_docstring()
        elif self._callable.__name__ == 'create_group':
            h5tbx.Group.__dict__[self._callable.__name__].__doc__ = self.get_docstring()
        else:
            h5tbx.File.__dict__['__init__'].__doc__ = self.get_docstring()

    def add_additional_parameters(self, additional_parameters: Dict):
        """Adds additional parameters to the docstring

        Parameters
        ----------
        additional_parameters: Dict
            Dictionary of additional parameters to add to the docstring
            Must contain
        """
        _required = ('description', 'default', 'type')
        for k, v in additional_parameters.items():
            for _r in _required:
                if _r not in v:
                    raise ValueError(f'Item "{_r}" missing for additional parameter "{k}"')
        for k, v in additional_parameters.items():
            self.additional_parameters.update({k: v})

    @staticmethod
    def parse_parameter(param_str):
        # Regular expression pattern to extract parameter name, type, and default value
        pattern = r'^\s*([\w\d_*]+)\s*:\s*(.+?)(?:\s*,\s*optional(?:\s*=\s*(.*))?)?$'

        # Matching the regex pattern with the parameter string
        match = re.match(pattern, param_str)

        if match:
            param_name = match.group(1).strip()
            param_type = match.group(2).strip()
            param_default = match.group(3).strip() if match.group(3) else None
            return param_name, param_type, param_default

    @staticmethod
    def parse_docstring(docstring):
        """Parses a docstring into abstract, parameters, returns and notes"""
        abstract = None
        kw = []
        rkw = []
        notes_lines = []

        if not docstring:
            return abstract, kw, rkw, notes_lines

        lines = docstring.strip().split('\n')

        current_section = None
        nlines = len(lines)
        for iline, line in enumerate(lines):
            line = line.strip()

            if line in ['Parameters', 'Returns', 'Notes']:
                current_section = line.lower()
                if abstract is None:
                    abstract = [l.strip() for l in lines[:iline]]
            elif current_section == 'parameters':
                if line:
                    # if current_param is None:
                    param_info = line.split(':')
                    if len(param_info) >= 2:
                        param_name, param_type, param_default = DocStringParser.parse_parameter(line)

                        desc_lines = []
                        for i in range(iline + 1, nlines):
                            if lines[i] == '' or DocStringParser.parse_parameter(lines[i]) is not None:
                                break
                            desc_lines.append(lines[i].strip())
                        desc = '\n\t'.join(desc_lines)
                        current_param = {
                            'name': param_name,
                            'type': param_type,
                            'default': param_default,
                            'description': desc.strip(),
                        }
                        kw.append(current_param)
            elif current_section == 'notes':
                notes_lines.append(line.strip())
            elif current_section == 'returns':
                param_info = line.split(':')
                if len(param_info) >= 2:
                    param_name, param_type, param_default = DocStringParser.parse_parameter(line)
                    desc_lines = []
                    for i in range(iline + 1, nlines):
                        if lines[i] == '' or DocStringParser.parse_parameter(lines[i]) is not None:
                            break
                        desc_lines.append(lines[i].strip())
                    desc = '\n\t'.join(desc_lines)
                    current_ret_param = {
                        'name': param_name,
                        'type': param_type,
                        'default': param_default,
                        'description': desc.strip(),
                    }
                    rkw.append(current_ret_param)

        return abstract, kw, rkw, notes_lines
