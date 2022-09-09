import pathlib
from itertools import count

import appdirs

_filecounter = count()
_dircounter = count()

_user_root_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))
user_dirs = {'root': _user_root_dir,
             'layouts': _user_root_dir / 'layouts',
             'standard_name_tables': _user_root_dir / 'standard_name_tables',
             'standard_name_table_translations': _user_root_dir / 'standard_name_table_translations',
             }

for _user_dir in user_dirs.values():
    _user_dir.mkdir(parents=True, exist_ok=True)

config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
config_filename = config_dir / 'h5rdmtoolbox.yaml'


# tmp folder name is individual for every call of the package:
_dircounter = count()
_root_tmp_dir = _user_root_dir / 'tmp'
user_dirs['tmp'] = _root_tmp_dir / f'tmp{len(list(_root_tmp_dir.glob("tmp*")))}'
user_dirs['tmp'].mkdir(parents=True, exist_ok=True)

testdir = pathlib.Path(__file__).parent / 'tests/data'
