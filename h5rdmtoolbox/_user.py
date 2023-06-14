import appdirs
import pathlib
import pkg_resources
import shutil
from itertools import count

_filecounter = count()
_dircounter = count()

_user_root_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))


class DirManger:
    """Directory Manager class"""

    def __init__(self):
        self.user_dirs = {'root': _user_root_dir,
                          'layouts': _user_root_dir / 'layouts',
                          'standard_name_tables': _user_root_dir / 'standard_name_tables',
                          'standard_name_table_translations': _user_root_dir / 'standard_name_table_translations',
                          }

        user_tmp_dir = self._get_dir('tmp')
        itmp = len(list(user_tmp_dir.glob("tmp*")))
        session_tmp_dir = user_tmp_dir / f'tmp{itmp}'
        while session_tmp_dir.exists():
            itmp += 1
            session_tmp_dir = user_tmp_dir / f'tmp{itmp}'

        session_tmp_dir.mkdir(parents=True, exist_ok=True)
        self._session_tmp_dir = session_tmp_dir

    def __getitem__(self, item):
        return self._get_dir(item)

    def names(self):
        return self.UserDir.keys()

    def __contains__(self, item):
        return item in self.UserDir.keys()

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
        if name == 'root':
            if not self.user_dirs['root'].exists():
                self.user_dirs['root'].mkdir(parents=True)
            return self.user_dirs['root']

        if name == 'layouts':
            if not self.user_dirs['layouts'].exists():
                self.user_dirs['layouts'].mkdir()

            layout_filenames = pathlib.Path(_get_pkg_resource_filename('data')).glob('*.hdf')
            for layout_filename in layout_filenames:
                shutil.copy2(layout_filename, self.user_dirs['layouts'] / layout_filename.name)

            return self.user_dirs['layouts']
        if name == 'standard_name_table_translations':
            if not self.user_dirs['standard_name_table_translations'].exists():
                self.user_dirs['standard_name_table_translations'].mkdir()
                # first copy the default data there:
                test_to_test = _get_pkg_resource_filename('data/test-to-Test-v1.yml')

                shutil.copy2(test_to_test, self.user_dirs['standard_name_table_translations'])
            return self.user_dirs['standard_name_table_translations']

        if name == 'standard_name_tables':
            if not self.user_dirs['standard_name_tables'].exists():
                # first copy the default data there:
                fluid_v1 = _get_pkg_resource_filename('data/fluid-v1.yml')
                piv_v1 = _get_pkg_resource_filename('data/piv-v1.yml')
                test_v1 = _get_pkg_resource_filename('data/Test-v1.yml')

                self.user_dirs['standard_name_tables'].mkdir()
                shutil.copy2(fluid_v1, self.user_dirs['standard_name_tables'])
                shutil.copy2(piv_v1, self.user_dirs['standard_name_tables'])
                shutil.copy2(test_v1, self.user_dirs['standard_name_tables'])
                shutil.copy2(test_v1, self.user_dirs['standard_name_tables'])
            return self.user_dirs['standard_name_tables']
        if name == 'tmp':
            # tmp folder name is individual for every call of the package:
            _root_tmp_dir = self._get_dir('root') / 'tmp'
            if not _root_tmp_dir.exists():
                _root_tmp_dir.mkdir()
            return _root_tmp_dir
        if name == 'session_tmp':
            if not self._session_tmp_dir.exists():
                self._session_tmp_dir.mkdir(parents=True)
            return self._session_tmp_dir
        raise ValueError(f'Unknown user directory name: "{name}"')


UserDir = DirManger()


def _get_pkg_resource_filename(fname):
    try:
        filename = pkg_resources.resource_filename('h5rdmtoolbox', fname)
    except TypeError:
        filename = pathlib.Path(__file__).parent / fname
    return filename


config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
config_filename = config_dir / 'h5rdmtoolbox.yaml'

