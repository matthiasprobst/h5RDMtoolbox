import pathlib
import shutil
import time
from itertools import count
from typing import Tuple

import appdirs
import importlib_resources

from ._version import __version__

USER_LOG_DIR = pathlib.Path(appdirs.user_log_dir('h5rdmtoolbox', version=__version__))
USER_DATA_DIR = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox', version=__version__))
USER_CACHE_DIR = pathlib.Path(appdirs.user_cache_dir('h5rdmtoolbox', version=__version__))
USER_LOG_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
USER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_filecounter = count()
_dircounter = count()

_now = time.time()


class DirManger:
    """Directory Manager class"""

    def __init__(self):
        toolbox_tmp_folder = USER_DATA_DIR / 'tmp'
        toolbox_tmp_folder.mkdir(parents=True, exist_ok=True)

        i = 0
        tmp_dir = toolbox_tmp_folder / f'tmp_{i}'
        while tmp_dir.exists():
            i += 1
            tmp_dir = toolbox_tmp_folder / f'tmp_{i}'
        try:
            tmp_dir.mkdir()
        except Exception:
            i += 1
            tmp_dir = toolbox_tmp_folder / f'tmp_{i}'

        self.user_dirs = {'root': USER_DATA_DIR,
                          'tmp': tmp_dir,
                          'convention': USER_DATA_DIR / 'convention',
                          'layouts': USER_DATA_DIR / 'layouts',
                          'repository': USER_DATA_DIR / 'repository',
                          'standard_name_tables': USER_DATA_DIR / 'standard_name_tables',
                          'cache': USER_DATA_DIR / 'cache'}
        self.clear_cache(6)

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

        copy_tbx_data = name == 'standard_name_tables' and not self.user_dirs['standard_name_tables'].exists()

        self.user_dirs[name].mkdir(parents=True, exist_ok=True)

        if name == 'layouts':

            layout_filenames = pathlib.Path(_get_pkg_resource_filename('data')).glob('*.hdf')
            for layout_filename in layout_filenames:
                shutil.copy2(layout_filename, self.user_dirs['layouts'] / layout_filename.name)

        if copy_tbx_data:
            # first copy the default data there:
            fluid_v1 = _get_pkg_resource_filename('data/fluid-v1.yml')
            piv_v1 = _get_pkg_resource_filename('data/piv-v1.yml')
            tutorial_standard_name_table = _get_pkg_resource_filename('data/tutorial_standard_name_table.yaml')

            shutil.copy2(fluid_v1, self.user_dirs['standard_name_tables'])
            shutil.copy2(piv_v1, self.user_dirs['standard_name_tables'])
            shutil.copy2(tutorial_standard_name_table, self.user_dirs['standard_name_tables'])

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
            shutil.rmtree(self.user_dirs['cache'])
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
        shutil.rmtree(self.user_dirs['cache'])
        shutil.rmtree(self.user_dirs['convention'])
        shutil.rmtree(self.user_dirs['standard_name_tables'])
        shutil.rmtree(self.user_dirs['layouts'])
        shutil.rmtree(self.user_dirs['tmp'], ignore_errors=True)


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
