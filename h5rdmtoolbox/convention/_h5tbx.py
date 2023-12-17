import pathlib
import sys

from . import generate
from .._user import UserDir
from ..errors import ImportConventionError

__this_dir__ = pathlib.Path(__file__)
convention_name = 'h5tbx'
convention_user_dir = UserDir['convention'] / convention_name


def build_convention():
    """Build the toolbox convention from the yaml file"""
    h5tbx_convention_yaml = __this_dir__.parent / f'../data/{convention_name}.yaml'
    convention_user_dir.mkdir(parents=True, exist_ok=True)
    generate.write_convention_module_from_yaml(h5tbx_convention_yaml)


if not (convention_user_dir / f'{convention_user_dir.name}.py').exists():
    build_convention()

sys.path.insert(0, str(UserDir['convention'] / convention_name))

import importlib

try:
    imported_module = importlib.import_module(convention_name)
    # Now, you can use the imported module as needed
    # For example:
    imported_module.cv
except NameError:
    raise ImportConventionError(
        f'The convention "{convention_name}" could not be imported. Please check the convention file content '
        f'(location: {UserDir["convention"] / convention_name}).')
except ImportError:
    print(f"Failed to import module {convention_name}")
