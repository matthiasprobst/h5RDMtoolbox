"""h5rdtoolbox repository"""

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'

import atexit
import pathlib
import shutil
import sys
from importlib.metadata import version as _version
from itertools import count

import appdirs

from . import conventions

# from .convention.time import datetime_str

__version__ = _version("h5rdmtoolbox")
user_data_dir = pathlib.Path(appdirs.user_data_dir(name))
sys.path.insert(0, str(user_data_dir.absolute()))

user_config_dir = pathlib.Path.home() / ".config" / name
if not user_config_dir.exists():
    user_config_dir.mkdir(parents=True)
user_config_filename = user_config_dir / f'{name}.yaml'

# tmp folder name is individual for every call of the package:
_dircounter = count()
_root_tmp_dir = user_data_dir / 'tmp'
user_tmp_dir = _root_tmp_dir / f'tmp{len(list(_root_tmp_dir.glob("tmp*")))}'

if not user_tmp_dir.exists():
    user_tmp_dir.mkdir(parents=True)

testdir = pathlib.Path(__file__).parent / 'tests/data'


def set_loglevel(level):
    """setting logging level of all modules"""
    from .x2hdf import set_loglevel as x2hdf_set_loglevel
    from .h5wrapper import set_loglevel as h5wrapper_set_loglevel
    from .h5database import set_loglevel as h5database_set_loglevel
    from .conventions import set_loglevel as conventions_set_loglevel
    x2hdf_set_loglevel(level)
    h5wrapper_set_loglevel(level)
    h5database_set_loglevel(level)
    conventions_set_loglevel(level)


__all__ = ['__version__', '__author__', 'user_data_dir', 'conventions']


@atexit.register
def clean_temp_data():
    """cleaning up the tmp directory"""
    if user_tmp_dir.exists():
        try:
            print(user_tmp_dir)
            shutil.rmtree(user_tmp_dir)
        except RuntimeError as e:
            print(f'removing tmp folder "{user_tmp_dir}" failed due to "{e}". Best is you '
                  f'manually delete the directory.')
