"""h5rdtoolbox repository"""
import atexit
import logging
import pathlib
import shutil
import warnings

from . import config
from . import wrapper
from ._logger import create_package_logger
from ._user import _root_tmp_dir, user_dirs
from ._version import __version__
from .config import user_config_filename
from .database import filequery
from .utils import generate_temporary_filename, generate_temporary_directory
from .wrapper import core
from .wrapper.core import lower

name = 'h5rdmtoolbox'
__author__ = 'Matthias Probst'

core_logger = create_package_logger('h5rdmtoolbox')


def set_loglevel(logger, level):
    """set the loglevel of the whole package"""
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    old_level = logger.level
    logger.setLevel(level.upper())
    for h in logger.handlers:
        h.setLevel(level.upper())
    logger.debug(f'changed logger level for {logger.name} from {old_level} to {level}')


CONFIG = config.CONFIG

set_loglevel(core_logger, CONFIG.INIT_LOGGER_LEVEL)

# global instance:
h5tbxParams = {'convention': config.CONFIG['CONVENTION'],
               'H5File': core.H5File,
               'H5Dataset': core.H5Dataset,
               'H5Group': core.H5Group}


def use(convention_name: str) -> None:
    """Select the convention for the HDF5 wrapper class(es)

    Parameters
    ----------
    convention_name: str
        Name of the convention
    """
    if convention_name == 'default' or convention_name is None:
        if h5tbxParams['convention'] != convention_name:
            core_logger.info('Switched to "default"')
        h5tbxParams['convention'] = convention_name
        h5tbxParams['H5File'] = core.H5File
        h5tbxParams['H5Dataset'] = core.H5Dataset
        h5tbxParams['H5Group'] = core.H5Group
        return

    if convention_name == 'cflike':
        # only now import the cflike sub-package if its dependencies are installed
        try:
            from .wrapper import cflike
        except ImportError:
            raise ImportError('It seems like the dependencies for the cflike package are missing. Consider '
                              'installing them. Get all dependencies by calling "pip install h5rdmtoolbox[cflike]"')
        if h5tbxParams['convention'] != convention_name:
            core_logger.info(f'Switched to "{convention_name}"')
        h5tbxParams['convention'] = convention_name
        h5tbxParams['H5File'] = cflike.H5File
        h5tbxParams['H5Dataset'] = cflike.H5Dataset
        h5tbxParams['H5Group'] = cflike.H5Group
        return

    raise ValueError(f'Unknown convention name: "{convention_name}"')


class H5File:
    """Interface class to wrapper class around HDF5/h5py.File"""

    def __new__(cls, *args, **kwargs):
        return h5tbxParams['H5File'](*args, **kwargs)

    def __str__(self) -> str:
        return h5tbxParams['H5File'].__str__(self)

    def __repr__(self) -> str:
        return h5tbxParams['H5File'].__repr__(self)

    @staticmethod
    def H5Dataset():
        """Return hdf dataset class  of set convention wrapper"""
        return h5tbxParams['H5Dataset']

    @staticmethod
    def H5Group():
        """Return hdf group class  of set convention wrapper"""
        return h5tbxParams['H5Group']


class H5Files:
    """Interface class to wrapper class around HDF5/h5py.File"""

    def __new__(cls, *args, **kwargs):
        use(config.CONFIG['CONVENTION'])
        file_instance = kwargs.get('file_instance', None)
        fileinstance = kwargs.pop('fileinstance', None)
        if fileinstance is not None:
            warnings.warn('Please use file_instance instead of fileinstance', DeprecationWarning)
            file_instance = fileinstance
        if file_instance is None:
            kwargs['file_instance'] = h5tbxParams['H5File']
        return filequery.Files(*args, **kwargs)


@atexit.register
def clean_temp_data(full: bool = False):
    """cleaning up the tmp directory"""
    failed_dirs = []
    failed_dirs_file = _root_tmp_dir / 'failed.txt'
    if full:
        if _root_tmp_dir.exists():
            shutil.rmtree(_root_tmp_dir)
            _root_tmp_dir.mkdir(exist_ok=True, parents=True)
        return
    _tmp_session_dir = user_dirs["tmp"]
    if _tmp_session_dir.exists():
        try:
            # logger not available anymore
            # core_logger.debug(f'Attempting to delete {_tmp_session_dir}')
            shutil.rmtree(user_dirs['tmp'])
            # core_logger.debug(f'Successfully deleted {_tmp_session_dir}')
        except PermissionError as e:
            failed_dirs.append(user_dirs['tmp'])
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
        core_logger.debug(f'No user tmp dir not found: {_tmp_session_dir}')


__all__ = ['__version__', '__author__', 'user_dirs', 'use', 'core_logger', 'user_config_filename',
           'generate_temporary_filename', 'generate_temporary_directory']
