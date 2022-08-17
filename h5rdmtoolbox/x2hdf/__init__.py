from ._logger import logger, _file_handler, _stream_handler
from .piv import pivview, openpiv
from .piv.interface import PIVPlane, PIVMultiPlane, PIVSnapshot


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    logger.setLevel(level.upper())
    _file_handler.setLevel(level.upper())
    _stream_handler.setLevel(level.upper())


__all__ = ['set_loglevel', 'pivview', 'openpiv',
           'PIVSnapshot', 'PIVPlane', 'PIVMultiPlane']
