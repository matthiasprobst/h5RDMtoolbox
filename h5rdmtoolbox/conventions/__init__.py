""""

This sub-package provides conventions such as standard_names

The concept of standard_names is adopted from the climate forecast community (see cfconventions.org)
The standrd name definitions (name, description, units) are to be provided in XML files. Two xml files
are provided by this sub-packages (fluid and piv). As the projec is under development, they are generated
in the fluid.py file but in later versions the conventions will only be provided as xml files.
"""

from . import data, standard_names, layout
from . import layout
from ._logger import logger
from .utils import xml2dict, dict2xml, is_valid_email_address


def set_loglevel(level):
    if isinstance(level, str):
        logger.setLevel(level.upper())
    else:
        logger.setLevel(level)


datetime_str = '%Y-%m-%dT%H:%M:%SZ%z'

__all__ = ['standard_names', 'layout', 'datetime_str', 'set_loglevel']
