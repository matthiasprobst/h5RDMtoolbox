"""
Subpackage wrapper:
Contains wrapper classes
"""

from . import _logger
from . import core


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    _logger.logger.setLevel(level)
    for handler in _logger.logger.handlers:
        handler.setLevel(level)

__all__ = ['set_loglevel']
