import appdirs
import pathlib
import pkg_resources
import shutil
from itertools import count
from typing import Tuple

_filecounter = count()
_dircounter = count()

_user_root_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))


class DirManger:
    """Directory Manager class"""

    def __init__(self):
        self.user_dirs = {'root': _user_root_dir,
                          'tmp': _user_root_dir / 'tmp',
                          'layouts': _user_root_dir / 'layouts',
                          'standard_name_tables': _user_root_dir / 'standard_name_tables',
                          'cache': _user_root_dir / 'cache'}

        user_tmp_dir = self._get_dir('tmp')
        i_tmp = len(list(user_tmp_dir.glob("tmp*")))
        session_tmp_dir = user_tmp_dir / f'tmp{i_tmp}'
        while session_tmp_dir.exists():
            i_tmp += 1
            session_tmp_dir = user_tmp_dir / f'tmp{i_tmp}'

        session_tmp_dir.mkdir(parents=True, exist_ok=True)
        self._session_tmp_dir = session_tmp_dir

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
            tutorial_standard_name_table = _get_pkg_resource_filename('data/tutorial_standard_name_table.yml')

            shutil.copy2(fluid_v1, self.user_dirs['standard_name_tables'])
            shutil.copy2(piv_v1, self.user_dirs['standard_name_tables'])
            shutil.copy2(tutorial_standard_name_table, self.user_dirs['standard_name_tables'])

        return self.user_dirs[name]

    def clear_cache(self):
        """Clear the cache directory."""
        shutil.rmtree(self.user_dirs['cache'])


UserDir = DirManger()


def _get_pkg_resource_filename(fname):
    try:
        filename = pkg_resources.resource_filename('h5rdmtoolbox', fname)
    except TypeError:
        filename = pathlib.Path(__file__).parent / fname
    return filename


config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
config_filename = config_dir / 'h5rdmtoolbox.yaml'
