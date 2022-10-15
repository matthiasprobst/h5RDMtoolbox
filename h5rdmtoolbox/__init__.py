"""h5rdtoolbox repository"""

import atexit
import pathlib
import shutil

from . import conventions
from . import tutorial
from ._user import _root_tmp_dir
from ._user import user_dirs
from ._version import __version__
from .conventions import set_loglevel as conventions_set_loglevel
from .database import set_loglevel as database_set_loglevel
from .utils import generate_temporary_filename, generate_temporary_directory
from .wrapper import set_loglevel as wrapper_set_loglevel
from .wrapper.h5file import H5File
# from .wrapper.h5flow import H5Flow
# from .wrapper.h5piv import H5PIV

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'


def set_loglevel(level):
    """setting logging level of all modules"""
    wrapper_set_loglevel(level)
    database_set_loglevel(level)
    conventions_set_loglevel(level)


@atexit.register
def clean_temp_data():
    """cleaning up the tmp directory"""
    failed_dirs = []
    failed_dirs_file = _root_tmp_dir / 'failed.txt'
    if user_dirs['tmp'].exists():
        try:
            shutil.rmtree(user_dirs['tmp'])
        except PermissionError as e:
            failed_dirs.append(user_dirs['tmp'])
            print(f'removing tmp folder "{user_dirs["tmp"]}" failed due to "{e}". Best is you '
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


__all__ = ['tutorial', '__version__', '__author__', 'user_dirs', 'conventions', 'H5File', 'H5Flow', 'H5PIV',
           'generate_temporary_filename', 'generate_temporary_directory']
