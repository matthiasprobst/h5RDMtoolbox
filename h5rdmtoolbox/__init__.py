"""h5rdtoolbox repository"""

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'

import atexit
import shutil

from . import conventions


# from .convention.time import datetime_str


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


from .h5wrapper import H5File, H5Flow, H5PIV, open_wrapper
from .utils import generate_temporary_filename, generate_temporary_directory, user_data_dir, user_tmp_dir
from ._version import __version__
from . import tutorial

__all__ = ['__version__', '__author__', 'user_data_dir', 'conventions', 'H5File', 'H5Flow', 'H5PIV', 'open_wrapper',
           'generate_temporary_filename', 'generate_temporary_directory', 'tutorial']


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
