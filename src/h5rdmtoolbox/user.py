import os
import pathlib
import shutil
import time
from itertools import count
from typing import Tuple

import appdirs
import importlib_resources

from ._version import __version__

USER_LOG_DIR = pathlib.Path(
    os.environ.get("H5RDMTOOLBOX_LOG_DIR")
    or appdirs.user_log_dir('h5rdmtoolbox', version=__version__)
)
USER_DATA_DIR = pathlib.Path(
    os.environ.get("H5RDMTOOLBOX_USER_DATA_DIR")
    or appdirs.user_data_dir('h5rdmtoolbox', version=__version__)
)
CACHE_DIR = pathlib.Path(
    os.environ.get("H5RDMTOOLBOX_CACHE_DIR")
    or appdirs.user_cache_dir('h5rdmtoolbox')
)



USER_CACHE_DIR = CACHE_DIR  # deprecated name

_filecounter = count()
_dircounter = count()

_now = time.time()


def _create_session_tmp_dir(tmp_root: pathlib.Path) -> pathlib.Path:
    tmp_root.mkdir(parents=True, exist_ok=True)
    for i in range(1000):
        tmp_dir = tmp_root / f'tmp_{os.getpid()}_{i}'
        try:
            tmp_dir.mkdir()
        except FileExistsError:
            continue
        except PermissionError:
            continue
        return tmp_dir
    raise PermissionError(f'Could not create a temporary directory in "{tmp_root}"')


def default_cache_dir(__version__: str) -> pathlib.Path:
    return CACHE_DIR


def cache_dir(__version__: str) -> pathlib.Path:
    return default_cache_dir(__version__)


class DirManger:
    """Directory Manager class"""

    def __init__(self):
        self.user_dirs = {'root': USER_DATA_DIR, 'tmp': None,
                          'repository': USER_DATA_DIR / 'repository', 'cache': CACHE_DIR}

    def __str__(self):
        dirs = ', '.join(f'{k}' for k in self.user_dirs.keys())
        return f'{self.__class__.__name__}({dirs})'

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, item):
        return self._get_dir(item)

    @property
    def names(self) -> Tuple[str]:
        """Get the names of the user directories."""
        return tuple(self.user_dirs.keys())

    def __contains__(self, item):
        return item in self.user_dirs

    def _get_dir(self, name: str) -> pathlib.Path:
        """Get a path to a file or directory in the user directory.

        Parameters
        ----------
        name : str
            The name of the file or directory.

        Returns
        -------
        pathlib.Path
            The path to the file or directory.
        """
        if name not in self.names:
            raise ValueError(f'Unknown user directory name: "{name}"')

        if name == 'tmp' and self.user_dirs[name] is None:
            self.user_dirs[name] = _create_session_tmp_dir(USER_DATA_DIR / 'tmp')
        self.user_dirs[name].mkdir(parents=True, exist_ok=True)

        return self.user_dirs[name]

    def clear_cache(self, delta_days: int, utime: bool = False):
        """Clear the cache directory. The delta_days arguments will be used
        to delete files older than delta_days days. This is only applied to files

        Parameters
        ----------
        delta_days : int
            The number of days to keep the files in the cache.
        utime : bool
            If True, the file access time will be used to determine the age of the file.
            Otherwise, the file creation time will be used.
        """
        if delta_days == 0:
            shutil.rmtree(self.user_dirs['cache'], ignore_errors=True)
            return
        if self.user_dirs['cache'].exists():
            for f in self.user_dirs['cache'].iterdir():
                if f.is_file():
                    # get the file creation time
                    if utime:
                        fct = f.stat().st_atime
                    else:
                        fct = f.stat().st_ctime
                    dt = _now - fct
                    if dt > delta_days * 86400:
                        f.unlink()

    def reset(self):
        """Deletes all user data"""
        for name in ('cache', 'repository', 'tmp'):
            directory = self.user_dirs[name]
            if directory is not None and directory.exists():
                shutil.rmtree(directory)



UserDir = DirManger()


def _get_pkg_resource_filename(fname: str) -> pathlib.Path:
    """Returns a filename or folder in the package data folder."""
    return importlib_resources.files('h5rdmtoolbox') / fname
    # try:
    #     filename = importlib_resources.files('h5rdmtoolbox') / fname
    # except TypeError:
    #     filename = pathlib.Path(__file__).parent / fname
    # return filename


config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
config_filename = config_dir / 'h5rdmtoolbox.yaml'
