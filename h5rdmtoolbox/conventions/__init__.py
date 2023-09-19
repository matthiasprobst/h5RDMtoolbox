""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)

A convention (class `Convention` includes a set of standard attributes, which are defined in a YAML file.

Helpful functions:
 - `get_registered_conventions`
 - `get_current_convention`
"""

from h5rdmtoolbox.utils import create_tbx_logger

logger = create_tbx_logger('conventions')

from .core import Convention, from_yaml, from_zenodo, get_current_convention, from_zenodo, get_registered_conventions
from .standard_attributes import StandardAttribute
from . import standard_names
from . import _h5tbx as __h5tbx_convention

__all__ = ['Convention', 'from_yaml', 'from_zenodo',
           'get_current_convention', 'get_registered_conventions',
           'from_zenodo', 'StandardAttribute']
