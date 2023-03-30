""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)
The standrd name definitions (name, description, units) are to be provided in XML files. Two xml files
are provided by this sub-packages (fluid and piv). As the projec is under development, they are generated
in the fluid.py file but in later versions the conventions will only be provided as xml files.
"""

from typing import Callable, List

from . import standard_attribute
from ._logger import logger
from .layout import H5Layout
from .standard_attribute import StandardAttribute
from .standard_name import StandardName, StandardNameTable
from .utils import dict2xml, is_valid_email_address


def list_standard_attributes(obj: Callable = None):
    """List all registered standard attributes

    Returns
    -------
    List[StandardAttribute]
        List of all registered standard attributes
    """
    if None:
        return standard_attribute.cache.REGISTERED_PROPERTIES
    return standard_attribute.cache.REGISTERED_PROPERTIES.get(type(obj), {})


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'
__all__ = ['H5Layout', 'datetime_str', 'set_loglevel',
           'StandardName', 'StandardNameTable', 'StandardAttribute']
