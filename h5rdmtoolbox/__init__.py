"""h5rdtoolbox repository"""

import atexit
import pathlib
import shutil

from . import config
from . import wrapper
from ._user import _root_tmp_dir, user_dirs
from ._version import __version__
from .utils import generate_temporary_filename, generate_temporary_directory
from .wrapper import cflike
from .wrapper import core

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'

# global instance:
h5tbxParams = {'H5File': core.H5File, 'H5Dataset': core.H5Dataset, 'H5Group': core.H5Group}


def use(cname: str) -> None:
    """Select the convention for the HDF5 wrapper class(es)"""

    if cname == 'default':
        h5tbxParams['convention'] = config.CONFIG['CONVENTION']
        h5tbxParams['H5File'] = core.H5File
        h5tbxParams['H5Dataset'] = core.H5Dataset
        h5tbxParams['H5Group'] = core.H5Group

    elif cname == 'cflike':
        h5tbxParams['convention'] = config.CONFIG['CONVENTION']
        h5tbxParams['H5File'] = cflike.H5File
        h5tbxParams['H5Dataset'] = cflike.H5Dataset
        h5tbxParams['H5Group'] = cflike.H5Group


class H5File:
    """Interface class to wrapper class around HDF5/h5py.File"""

    def __new__(cls, *args, **kwargs):
        use(config.CONFIG['CONVENTION'])
        return h5tbxParams['H5File'](*args, **kwargs)


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


__all__ = ['__version__', '__author__', 'user_dirs', 'use',
           'generate_temporary_filename', 'generate_temporary_directory']
