import pathlib
import appdirs
from itertools import count
_filecounter = count()
_dircounter = count()
user_data_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))

user_config_dir = pathlib.Path.home() / ".config" / 'h5rdmtoolbox'
if not user_config_dir.exists():
    user_config_dir.mkdir(parents=True)
user_config_filename = user_config_dir / 'h5rdmtoolbox.yaml'

# tmp folder name is individual for every call of the package:
_dircounter = count()
_root_tmp_dir = user_data_dir / 'tmp'
user_tmp_dir = _root_tmp_dir / f'tmp{len(list(_root_tmp_dir.glob("tmp*")))}'

if not user_tmp_dir.exists():
    user_tmp_dir.mkdir(parents=True)

testdir = pathlib.Path(__file__).parent / 'tests/data'