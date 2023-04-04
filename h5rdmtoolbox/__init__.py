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
from . import cache
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

from . import conventions

cv_h5py = conventions.Convention('h5py')
cv_h5py.register()

cv = conventions.Convention('tbx')
cv.add(attr_cls=conventions.title.TitleAttribute,
       target_cls=core.File,
       add_to_method=True,
       position={'before': 'layout'},
       optional=True)
cv.add(attr_cls=conventions.StandardAttribute.AnyString('institution'),
       target_cls=core.File,
       add_to_method=True,
       position={'before': 'layout'},
       optional=True)
cv.add(attr_cls=conventions.references.ReferencesAttribute,
       target_cls=core.File,
       add_to_method=True,
       position={'before': 'layout'},
       optional=True)
cv.add(attr_cls=conventions.standard_name.StandardNameTableAttribute,
       target_cls=core.File,
       add_to_method=True,
       position={'before': 'layout'},
       optional=True)
cv.add(attr_cls=conventions.standard_name.StandardNameTableAttribute,
       target_cls=core.Dataset,
       add_to_method=False)
cv.add(attr_cls=conventions.standard_name.StandardNameTableAttribute,
       target_cls=core.Group,
       add_to_method=False)
cv.add(attr_cls=conventions.standard_name.StandardNameAttribute,
       target_cls=core.Dataset,
       position={'after': 'name'},
       add_to_method=True,
       optional=False,
       alt='long_name')
cv.add(attr_cls=conventions.units.UnitsAttribute,
       target_cls=core.Dataset,
       add_to_method=True,
       position={'after': 'name'},
       optional=False)
cv.add(attr_cls=conventions.long_name.LongNameAttribute,
       target_cls=core.Dataset,
       add_to_method=True,
       position={'after': 'name'},
       optional=False,
       alt='standard_name')
cv.add(attr_cls=conventions.long_name.LongNameAttribute,
       target_cls=core.Group,
       add_to_method=True,
       position={'after': 'name'},
       optional=True,)
cv.add(attr_cls=conventions.comment.CommentAttribute,
       target_cls=core.Group,
       add_to_method=True,
       position={'after': 'long_name'},
       optional=True,)
cv.add(attr_cls=conventions.comment.CommentAttribute,
       target_cls=core.Dataset,
       add_to_method=True,
       position={'after': 'long_name'},
       optional=True,)
cv.add(attr_cls=conventions.respuser.RespUserAttribute,
       target_cls=core.Dataset,
       add_to_method=True,
       position={'after': 'comment'},
       optional=True,)
cv.add(attr_cls=conventions.respuser.RespUserAttribute,
       target_cls=core.Group,
       add_to_method=True,
       position={'before': 'attrs'},
       optional=True,)
cv.add(attr_cls=conventions.respuser.RespUserAttribute,
       target_cls=core.File,
       add_to_method=True,
       position={'after': 'mode'},
       optional=True,)
cv.register()

use = conventions.use

File = core.File


class Files:
    """Class to access multiple files at once"""

    def __new__(cls, *args, **kwargs):
        # use(config['default_convention'])
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
