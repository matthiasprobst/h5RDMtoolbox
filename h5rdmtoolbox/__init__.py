"""h5rdtoolbox repository"""

import atexit
import pathlib
import shutil

from . import config
from . import conventions
from ._user import _root_tmp_dir
from ._user import user_dirs
from ._version import __version__
from .utils import generate_temporary_filename, generate_temporary_directory

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'

global H5File, H5Dataset, H5Group


def use_wrapper_convention(cname: str):
    """Select the convention for the HDF5 wrapper class(es)"""
    global H5File, H5Dataset, H5Group
    if cname == 'default':
        from .wrapper import core

        H5File = core.H5File
        H5Dataset = core.H5Dataset
        H5Group = core.H5Group

    elif cname == 'cflike':
        from .wrapper import cflike

        H5File = cflike.H5File
        H5Dataset = cflike.H5Dataset
        H5Group = cflike.H5Group


# select the default convention:
use_wrapper_convention(config.CONVENTION)


# if config.CONVENTION == 'default':
#     from . import wrapper
#
#     H5File = wrapper.H5File
#     H5Dataset = wrapper.h5file.H5Dataset
#     H5Group = wrapper.h5file.H5Group
#
# elif config.CONVENTION == 'cflike':
#     from .wrapper import cflike
#
#     H5File = cflike.H5File
#     H5Dataset = cflike.H5Dataset
#     H5Group = cflike.H5Group


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


__all__ = ['__version__', '__author__', 'user_dirs', 'conventions', 'H5File',
           'generate_temporary_filename', 'generate_temporary_directory']
