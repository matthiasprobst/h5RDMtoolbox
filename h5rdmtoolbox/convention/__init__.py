""""

This sub-package provides convention such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)

A convention (class `Convention` includes a set of standard attributes, which are defined in a YAML file.

Helpful functions:
 - `get_registered_conventions`
 - `get_current_convention`
"""

import pathlib

from .core import Convention, from_yaml, from_repo, get_current_convention, from_zenodo, get_registered_conventions, \
    yaml2jsonld
from .standard_attributes import StandardAttribute
from .toolbox_validators import get_list_of_validators
from ..user import UserDir

__this_dir__ = pathlib.Path(__file__).parent

convention_user_dir = UserDir['convention'] / 'h5tbx'


def build_convention():
    """Build the toolbox convention from the yaml file"""
    from . import generate
    h5tbx_convention_yaml = __this_dir__.parent / f'data/h5tbx.yaml'
    convention_user_dir.mkdir(parents=True, exist_ok=True)
    generate.write_convention_module_from_yaml(h5tbx_convention_yaml)


if not (convention_user_dir / f'h5tbx.py').exists():
    build_convention()

__all__ = ['Convention', 'from_yaml', 'from_zenodo', 'from_repo',
           'get_current_convention', 'get_registered_conventions',
           'from_zenodo', 'StandardAttribute', 'yaml2jsonld',
           'get_list_of_validators']
