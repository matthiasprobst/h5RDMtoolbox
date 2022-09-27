import pathlib
import shutil
from itertools import count

import appdirs
import pkg_resources

_filecounter = count()
_dircounter = count()

_user_root_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))
user_dirs = {'root': _user_root_dir,
             'layouts': _user_root_dir / 'layouts',
             'standard_name_tables': _user_root_dir / 'standard_name_tables',
             'standard_name_table_translations': _user_root_dir / 'standard_name_table_translations',
             }

if not user_dirs['root'].exists():
    user_dirs['root'].mkdir(parents=True)


def _get_pkg_resource_filename(fname):
    try:
        filename = pkg_resources.resource_filename('h5rdmtoolbox', fname)
    except TypeError:
        filename = pathlib.Path(__file__).parent / fname
    return filename


if not user_dirs['standard_name_tables'].exists():
    # first copy the default data there:
    fluid_v1 = _get_pkg_resource_filename('data/fluid-v1.yml')
    piv_v1 = _get_pkg_resource_filename('data/piv-v1.yml')
    test_v1 = _get_pkg_resource_filename('data/Test-v1.yml')

    user_dirs['standard_name_tables'].mkdir()
    shutil.copy2(fluid_v1, user_dirs['standard_name_tables'])
    shutil.copy2(piv_v1, user_dirs['standard_name_tables'])
    shutil.copy2(test_v1, user_dirs['standard_name_tables'])
    shutil.copy2(test_v1, user_dirs['standard_name_tables'])

if not user_dirs['layouts'].exists():
    user_dirs['layouts'].mkdir()
if not user_dirs['standard_name_table_translations'].exists():
    user_dirs['standard_name_table_translations'].mkdir()
    # first copy the default data there:
    test_to_test = _get_pkg_resource_filename('data/test-to-Test-v1.yml')

    shutil.copy2(test_to_test, user_dirs['standard_name_table_translations'])

config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
config_filename = config_dir / 'h5rdmtoolbox.yaml'

# tmp folder name is individual for every call of the package:
_root_tmp_dir = _user_root_dir / 'tmp'
itmp = len(list(_root_tmp_dir.glob("tmp*")))
user_dirs['tmp'] = _root_tmp_dir / f'tmp{itmp}'
while user_dirs['tmp'].exists():
    itmp += 1
    user_dirs['tmp'] = _root_tmp_dir / f'tmp{itmp}'

user_dirs['tmp'].mkdir(parents=True, exist_ok=True)

testdir = pathlib.Path(__file__).parent / '../tests/data'
