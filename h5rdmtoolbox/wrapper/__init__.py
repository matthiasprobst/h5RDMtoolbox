"""
Subpackage wrapper:
Contains wrapper classes
"""

from . import _logger
from . import core
from .. import config

global H5File, H5Dataset, H5Group


def use(cname: str):
    """Select the convention for the HDF5 wrapper class(es)"""
    global H5File, H5Dataset, H5Group
    if cname == 'default':
        from . import core

        H5File = core.H5File
        H5Dataset = core.H5Dataset
        H5Group = core.H5Group

    elif cname == 'cflike':
        from . import cflike

        H5File = cflike.H5File
        H5Dataset = cflike.H5Dataset
        H5Group = cflike.H5Group


use(config.CONVENTION)


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    _logger.logger.setLevel(level)
    for handler in _logger.logger.handlers:
        handler.setLevel(level)


__all__ = ['set_loglevel']
