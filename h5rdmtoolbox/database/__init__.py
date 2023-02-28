from ._logger import logger
from .filequery import Files


def set_loglevel(level):
    """setting the logging level of sub-package wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


__all__ = ['logger', 'set_loglevel', 'Files']
