"""
Subpackage wrapper:
Contains wrapper classes
"""

from . import _logger
from .accessory import register_special_property, register_special_dataset
from .core import H5File


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    _logger.logger.setLevel(level)
    for handler in _logger.logger.handlers:
        handler.setLevel(level)


__all__ = ['set_loglevel', 'H5File']
