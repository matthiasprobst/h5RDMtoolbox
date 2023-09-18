import pathlib
import sys

from . import generate
from .._user import UserDir

__this_dir__ = pathlib.Path(__file__)
convention_name = 'h5tbx'
convention_user_dir = UserDir['conventions'] / convention_name


def build_convention():
    h5tbx_convention_yaml = __this_dir__.parent / f'../data/{convention_name}.yaml'
    convention_user_dir.mkdir(parents=True, exist_ok=True)
    generate.write_convention_module_from_yaml(h5tbx_convention_yaml)


if not (convention_user_dir / 'convention.py').exists():
    build_convention()

sys.path.insert(0, str(UserDir['conventions'] / convention_name))

import importlib
try:
    imported_module = importlib.import_module(convention_name)
    # Now, you can use the imported module as needed
    # For example:
    imported_module.cv
except ImportError:
    print(f"Failed to import module {convention_name}")
