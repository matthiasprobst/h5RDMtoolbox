from datetime import datetime
from itertools import count
from pathlib import Path
from re import sub as re_sub

from cv2 import imread as cv2_imread
from dateutil.tz import tzlocal
from h5py import File
from pco_tools import pco_reader as pco

from . import __version__
from . import user_tmp_dir

_filecounter = count()
_dircounter = count()


def remove_special_chars(input_string, keep_special='/_', replace_spaces='_'):
    """Generally removes all characters that are no number
    or letter. Per default, underscores and forward slashes
    are kept and spaces are replaced with underscores.

    Typically used to clean up dataset names that contain special
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


def generate_temporary_filename(prefix='tmp', suffix: str = None) -> Path:
    """generates a temporary filename in user tmp file directory

    Parameters
    ----------
    prefix: str, optional='tmp'
        prefix string to put in front of name
    suffix: str, optional=None
        suffix (including '.')

    Returns
    -------
    tmp_filename: Path
        The generated temporary filename
    """
    _filename = user_tmp_dir / f"{prefix}{next(_filecounter)}{suffix}"
    while _filename.exists():
        _filename = user_tmp_dir / f"{prefix}{next(_filecounter)}{suffix}"
    return _filename


def generate_temporary_directory(prefix='tmp') -> Path:
    """generates a temporary directory in user tmp file directory

    Parameters
    ----------
    prefix: str, optional='tmp'
        prefix string to put in front of name

    Returns
    -------
    tmp_filename: Path
        The generated temporary filename
    """
    _dir = user_tmp_dir / f"{prefix}{next(_filecounter)}"
    _dir.mkdir(parents=True)
    return _dir


def generate_time_str(dtime: datetime, fmt: str) -> str:
    """Converts datetime to string. Needed to fix bug in datetime module for
    UTC offset.
    """
    zsplit = fmt.split('%z')
    if len(zsplit) == 1:
        return dtime.strftime(fmt)
    elif len(zsplit) == 2:
        return dtime.strftime(zsplit[0]) + datetime.now(tzlocal()).strftime('%z') + dtime.strftime(zsplit[1])
    else:
        raise ValueError(f'Invalid formatting string. Can only handle one %z formatter')


def touch_tmp_hdf5_file(touch=True) -> Path:
    """
    Generates a file path in directory h5wrapperclasses/.tmp
    with filename dsXXXX.hdf where XXXX is more or less a
    random number leading to a unique filename in the tmp
    location. The file is created and the file path is returned

    Returns
    --------
    hdf_filepath: Path
        file path to created hdf5 file
    touch : bool, optional=True
        touches the file

    """
    hdf_filepath = generate_temporary_filename(suffix='.hdf')
    if touch:
        with File(hdf_filepath, "w") as h5touch:
            h5touch.attrs['__h5rdmtoolbox_version__'] = __version__
    return hdf_filepath


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def _make_italic(string):
    return f'\x1B[3m{string}\x1B[0m'


def _make_bold(string):
    return f"{bcolors.BOLD}{string}{bcolors.ENDC}"


def _warningtext(string):
    return f"{bcolors.WARNING}{string}{bcolors.ENDC}"


def _failtext(string):
    return f"{bcolors.FAIL}{string}{bcolors.ENDC}"


def _oktext(string):
    return f"{bcolors.OKGREEN}{string}{bcolors.ENDC}"


def load_img(img_filepath: Path):
    """
    loads b16 or other file format
    """
    img_filepath = Path(img_filepath)
    if not img_filepath.exists():
        raise FileExistsError(f'Image "{img_filepath}" not found.')

    if img_filepath.suffix == '.b16':
        return pco.load(str(img_filepath))

    return cv2_imread(str(img_filepath), -1)