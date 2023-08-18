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

from .core import Convention, from_yaml, get_current_convention, from_zenodo

__all__ = ['Convention', 'from_yaml', 'get_current_convention', 'from_zenodo']

# from . import core
# from . import errors
# from .core import Convention, get_current_convention, get_registered_conventions, from_zenodo, from_yaml
# from .layout import Layout, validators
# from .layout.validators import Validator
# from .standard_attributes import StandardAttribute, __doc_string_parser__
# from .standard_attributes.validators.standard_name import StandardNameTable
#
# __all__ = ['Layout', 'validators', 'Validator', 'Convention',
#            'get_registered_conventions', 'get_current_convention',
#            'from_zenodo', 'from_yaml']
