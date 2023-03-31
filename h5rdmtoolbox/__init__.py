"""h5rdtoolbox repository"""
import atexit
import logging
import pathlib
import shutil
import warnings

from ._config import CONFIG
from ._config import user_config_filename, write_default_config, write_user_config, DEFAULT_CONFIG

config = CONFIG

from . import wrapper
from ._logger import create_package_logger
from ._user import UserDir
from ._version import __version__
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


set_loglevel(core_logger, config.init_logger_level)

# global instance:
h5tbxParams = {'convention': config['default_convention'],
               'File': core.File,
               'Dataset': core.Dataset,
               'Group': core.Group}


def get_current_convention_name():
    """Get the name of the currently selected convention"""
    return h5tbxParams['convention']


def use(convention_name: str) -> None:
    """Select the convention for the HDF5 wrapper class(es)

    Parameters
    ----------
    convention_name: str
        Name of the convention
    """
    if convention_name == 'h5py' or convention_name is None:
        if h5tbxParams['convention'] != convention_name:
            core_logger.info('Switched to convention "h5py"')
        h5tbxParams['convention'] = convention_name
        h5tbxParams['File'] = core.File
        h5tbxParams['Dataset'] = core.Dataset
        h5tbxParams['Group'] = core.Group
        return

    if convention_name == 'tbx':
        # only now import the tbx convention sub-package if its dependencies are installed
        try:
            from .wrapper import tbx
        except ImportError:
            raise ImportError('It seems like the dependencies for the tbx package are missing. Consider '
                              'installing them. Get all dependencies by calling "pip install h5rdmtoolbox[tbx]"')
        if h5tbxParams['convention'] != convention_name:
            core_logger.info(f'Switched to convention "{convention_name}"')
        h5tbxParams['convention'] = convention_name
        h5tbxParams['File'] = tbx.File
        h5tbxParams['Dataset'] = tbx.Dataset
        h5tbxParams['Group'] = tbx.Group
        return

    raise ValueError(f'Unknown convention name: "{convention_name}"')


class File:
    """Interface class to wrapper class around HDF5/h5py.File"""

    @staticmethod
    def __get_cls__(cls_name: str):
        """Return hdf class of set convention wrapper"""
        if not cls_name ('File', 'Dataset', 'Group'):
            raise ValueError(f'Unknown class name: "{cls_name}"')
        return h5tbxParams[cls_name]

    def __new__(cls, *args, **kwargs):
        return h5tbxParams['File'](*args, **kwargs)

    def __str__(self) -> str:
        return h5tbxParams['File'].__str__(self)

    def __repr__(self) -> str:
        return h5tbxParams['File'].__repr__(self)

    @staticmethod
    def Dataset():
        """Return hdf dataset class  of set convention wrapper"""
        return h5tbxParams['Dataset']

    @staticmethod
    def Group():
        """Return hdf group class  of set convention wrapper"""
        return h5tbxParams['Group']


class Files:
    """Class to access multiple files at once"""

    def __new__(cls, *args, **kwargs):
        use(config['default_convention'])
        file_instance = kwargs.get('file_instance', None)
        if file_instance is None:
            kwargs['file_instance'] = h5tbxParams['File']
        return filequery.Files(*args, **kwargs)


class H5File(File):
    """Deprecated class. Use "File" instead."""

    def __new__(cls, *args, **kwargs):
        warnings.warn('File is deprecated. Use "File" instead.', DeprecationWarning)
        return super().__new__(cls, *args, **kwargs)


class H5Files(Files):
    """Deprecated class. Use "Files" instead."""

    def __new__(cls, *args, **kwargs):
        warnings.warn('H5Files is deprecated. Use "Files" instead.', DeprecationWarning)
        super().__new__(cls, *args, **kwargs)


@atexit.register
def clean_temp_data(full: bool = False):
    """cleaning up the tmp directory"""
    failed_dirs = []
    failed_dirs_file = UserDir['tmp'] / 'failed.txt'
    if full:
        if UserDir['tmp'].exists():
            try:
                shutil.rmtree(UserDir['tmp'])
                UserDir['tmp'].mkdir(exist_ok=True, parents=True)
            except PermissionError as e:
                print(f'removing tmp folder "{UserDir["tmp"]}" failed due to "{e}".')
        return

    _tmp_session_dir = UserDir["session_tmp"]
    if _tmp_session_dir.exists():
        try:
            # logger not available anymore
            # core_logger.debug(f'Attempting to delete {_tmp_session_dir}')
            shutil.rmtree(UserDir['session_tmp'])
            # core_logger.debug(f'Successfully deleted {_tmp_session_dir}')
        except PermissionError as e:
            failed_dirs.append(UserDir['session_tmp'])
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


__all__ = ['__version__', '__author__', 'UserDir', 'use', 'core_logger', 'user_config_filename',
           'generate_temporary_filename', 'generate_temporary_directory']
