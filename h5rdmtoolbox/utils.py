"""utilities of the h5rdmtoolbox"""
import datetime
import h5py
import json
import pathlib
import pint
from h5py import File
from re import sub as re_sub
from typing import Union

from . import _user
from . import config
from ._version import __version__


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


def generate_temporary_filename(prefix='tmp', suffix: str = '') -> pathlib.Path:
    """generates a temporary filename in user tmp file directory

    Parameters
    ----------
    prefix: str, optional='tmp'
        prefix string to put in front of name
    suffix: str, optional=''
        suffix (including '.')

    Returns
    -------
    tmp_filename: pathlib.Path
        The generated temporary filename
    """
    _filename = _user.UserDir['session_tmp'] / f"{prefix}{next(_user._filecounter)}{suffix}"
    while _filename.exists():
        _filename = _user.UserDir['session_tmp'] / f"{prefix}{next(_user._filecounter)}{suffix}"
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
    _dir = _user.UserDir['session_tmp'] / f"{prefix}{next(_user._filecounter)}"
    while _dir.exists():
        _dir = _user.UserDir['session_tmp'] / f"{prefix}{next(_user._filecounter)}"
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


def create_special_attribute(h5obj: h5py.AttributeManager,
                             name: str,
                             value):
    """Allows writing more than the usual hdf5 attributes"""
    if isinstance(value, dict):
        # some value might be changed to a string first, like h5py objects
        for k, v in value.items():
            if isinstance(v, (h5py.Dataset, h5py.Group)):
                value[k] = v.name
        _value = json.dumps(value)
    elif isinstance(value, (h5py.Dataset, h5py.Group)):
        _value = value.name
    elif isinstance(value, str):
        _value = str(value)
    elif isinstance(value, pint.Quantity):
        _value = str(value)
    elif isinstance(value, pathlib.Path):
        _value = str(value)
    elif isinstance(value, datetime.datetime):
        _value = value.strftime(config.dtime_fmt)
    else:
        _value = value

    try:
        h5obj.create(name, data=_value)
    except TypeError:
        try:
            h5obj.create(name, data=str(_value))
        except TypeError as e2:
            raise RuntimeError(f'Error setting attribute to HDF object {self._parent}:'
                               f'\n  name: {name}\n  value: {value} \n  type: {type(value)}\n'
                               f'Original error: {e2}') from e2


def process_obj_filter_input(objfilter) -> Union[h5py.Dataset, h5py.Group]:
    if isinstance(objfilter, str):
        if objfilter.lower() == 'group':
            return h5py.Group
        if objfilter.lower() == 'groups':
            return h5py.Group
        if objfilter.lower() == 'dataset':
            return h5py.Dataset
        if objfilter.lower() == 'datasets':
            return h5py.Dataset
        if objfilter.lower() == '$group':
            return h5py.Group
        if objfilter.lower() == '$groups':
            return h5py.Group
        if objfilter.lower() == '$dataset':
            return h5py.Dataset
        if objfilter.lower() == '$datasets':
            return h5py.Dataset
        raise NameError(
            f'Expected values for argument objfilter are "dataset" or "group", not "{objfilter}"')
    return objfilter
