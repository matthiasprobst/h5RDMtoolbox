"""h5rdtoolbox repository"""

import logging
import pathlib
from logging.handlers import RotatingFileHandler

import appdirs

_logdir = pathlib.Path(appdirs.user_log_dir('h5rdmtoolbox'))
_logdir.mkdir(parents=True, exist_ok=True)

DEFAULT_LOGGING_LEVEL = logging.WARNING
_formatter = logging.Formatter(
    '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d_%H:%M:%S')

_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(DEFAULT_LOGGING_LEVEL)
_stream_handler.setFormatter(_formatter)

_file_handler = RotatingFileHandler(_logdir / 'h5rdmtoolbox.log')
_file_handler.setLevel(logging.DEBUG)  # log everything to file!
_file_handler.setFormatter(_formatter)

logger = logging.getLogger(__package__)
logger.addHandler(_stream_handler)
logger.addHandler(_file_handler)

import atexit
# noinspection PyUnresolvedReferences
import pint_xarray
import shutil
import xarray as xr
from typing import Union, Callable

from h5rdmtoolbox._cfg import set_config, get_config, get_ureg

pint_xarray.unit_registry = get_ureg()

from . import convention
from .convention.core import Convention
from . import wrapper
from ._user import UserDir
from ._version import __version__
from . import utils
from .wrapper.core import lower, Lower, File, Group, Dataset
from . import warnings, errors
from .wrapper import jsonld
from .wrapper.lazy import lazy
from .wrapper.h5attr import Attribute
from .wrapper.accessory import register_special_dataset
import json

name = 'h5rdmtoolbox'
__this_dir__ = pathlib.Path(__file__).parent
__author__ = 'Matthias Probst'
__author_orcid__ = 'https://orcid.org/0000-0001-8729-0482'


def get_package_meta():
    """Reads codemeta.json and returns it as dict"""
    with open(__this_dir__ / '../codemeta.json', 'r') as f:
        codemeta = json.loads(f.read())
    return codemeta


cv_h5py = convention.Convention(name='h5py',
                                contact=__author_orcid__)
cv_h5py.register()

use = convention.core.use
use(None)


def dump(src: Union[str, File, pathlib.Path],
         *args, **kwargs) -> None:
    """Call h5.dump() on the provided HDF5 file

    Parameters
    ----------
    src : str, File, pathlib.Path
        the HDF5 file or filename to dump. An object which has a hdf_filename attribute can also be provided.
    kwargs
        kwargs passed to h5.dump(). See h5.dump() for more information.
    """
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dump(*args, **kwargs)

    if isinstance(src, (str, pathlib.Path)):
        pass
    else:
        if hasattr(src, 'hdf_filename'):
            src = src.hdf_filename

    with File(src) as h5:
        return h5.dump(**kwargs)


def dumps(src: Union[str, File, pathlib.Path]):
    """Call h5.dumps() on the provided HDF5 file

    Parameters
    ----------
    src : str, File, pathlib.Path
        the HDF5 file or filename to dump. An object which has a hdf_filename attribute can also be provided.
    """
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dumps()

    if isinstance(src, (str, pathlib.Path)):
        pass
    else:
        if hasattr(src, 'hdf_filename'):
            src = src.hdf_filename

    with File(src) as h5:
        return h5.dumps()


def dump_jsonld(hdf_filename: Union[str, pathlib.Path],
                skipND: int = 1,
                structural: bool = True,
                semantic: bool = True,
                resolve_keys: bool = False,
                **kwargs) -> str:
    """Dump the JSON-LD representation of the file. With semantic=True and structural=False, the JSON-LD
    represents the semantic content only. To get a pure structural representation, set semantic=False, which
    will ignore any RDF content. If both are set to True, the JSON-LD will contain both structural and semantic.

    Parameters
    ----------
    hdf_filename : str, pathlib.Path
        the HDF5 file to dump.
    skipND : int=1
        Skip writing data of datasets with more then skipND dimensions. Only
        considered if structural=True.
    structural : bool=True
        Include structural information in the JSON-LD output.
    semantic : bool=True
        Include semantic information in the JSON-LD output.
    resolve_keys : bool=False
        Resolve keys in the JSON-LD output. This is used when semantic=True.
        If resolve_keys is False and an attribute name in the HDF5 file, which has
        a predicate is different in its name from the predicate, the attribute name is used.
        Example: an attribute "name" is associated with "foaf:lastName", then "name" is used
        and "name": "https://xmlns.com/foaf/0.1/lastName" is added to the context.

    """
    from .wrapper import jsonld
    if not structural and not semantic:
        raise ValueError('At least one of structural or semantic must be True.')
    if structural and not semantic:
        return jsonld.dump_file(hdf_filename, skipND=skipND)
    with File(hdf_filename) as h5:
        return jsonld.dumps(h5, structural=structural, resolve_keys=resolve_keys, **kwargs)


def register_dataset_decoder(decoder: Callable, decoder_name: str = None, overwrite: bool = False):
    """A decoder function takes a xarray.DataArray and a dataset as input and returns a xarray.DataArray
    It is called after the dataset is loaded into memory and before being returned to the user. Be careful:
    Multiple decoders can be registered, and they are called in the order of registration. Hence, your decoder
    may behave unexpectedly!
    """
    from .wrapper import ds_decoder
    if decoder_name is None:
        decoder_name = decoder.__name__
    registered_decorators = ds_decoder.registered_dataset_decoders
    if decoder_name in registered_decorators or decoder in registered_decorators.values():
        if not overwrite:
            raise ValueError(f'decoder "{decoder_name}" already registered. Name and function must be unique.')
    ds_decoder.registered_dataset_decoders[decoder_name] = decoder


atexit_verbose = False


@atexit.register
def clean_temp_data(full: bool = False):
    """cleaning up the tmp directory"""
    from ._user import _user_root_dir

    failed_dirs = []
    failed_dirs_file = UserDir['tmp'] / 'failed.txt'
    if full:
        root_tmp = _user_root_dir / 'tmp'
        if root_tmp.exists():
            try:
                shutil.rmtree(root_tmp)
                root_tmp.mkdir(exist_ok=True, parents=True)
            except PermissionError as e:
                print(f'removing tmp folder "{root_tmp}" failed due to "{e}".')
        return

    for _tmp_session_dir in [UserDir['tmp'], ]:
        if atexit_verbose:
            print(f'cleaning up tmp directory "{_tmp_session_dir}"')
        if _tmp_session_dir.exists():
            try:
                if atexit_verbose:
                    print(f'try deleting tmp in session dir: {_tmp_session_dir}')
                shutil.rmtree(_tmp_session_dir)
            except PermissionError as e:
                if atexit_verbose:
                    print(f'[!] failed deleting tmp session dir: {_tmp_session_dir}')
                failed_dirs.append(UserDir['tmp'])
                if atexit_verbose:
                    print(f'removing tmp folder "{_tmp_session_dir}" failed due to "{e}". Best is you '
                          f'manually delete the directory.')
            finally:
                lines = []
                if failed_dirs_file.exists():
                    with open(failed_dirs_file, 'r') as f:
                        lines = f.readlines()
                        for line in lines:
                            try:
                                shutil.rmtree(line.strip())
                            except Exception:
                                if pathlib.Path(line).exists():
                                    failed_dirs.append(line)

                if lines or failed_dirs:
                    with open(failed_dirs_file, 'w') as f:
                        for fd in failed_dirs:
                            f.writelines(f'{fd}\n')
                else:
                    failed_dirs_file.unlink(missing_ok=True)
        else:
            logger.debug(f'No user tmp dir not found: {_tmp_session_dir}')


xr.set_options(display_expand_data=False)

__all__ = ('__version__', '__author__', '__author_orcid__',
           'UserDir', 'use',
           'File', 'Group', 'Dataset', 'Attribute',
           'dump', 'dumps', 'cv_h5py', 'lower', 'Lower',
           'set_config', 'get_config', 'get_ureg',
           'Convention', 'jsonld', 'lazy')
