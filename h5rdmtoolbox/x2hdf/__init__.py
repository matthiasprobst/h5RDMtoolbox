from ._logger import logger, _file_handler, _stream_handler
from .cfd.ansys.cfx2hdf import cfx2hdf
from .piv import pivview
from .piv.interface import PIVPlane, PIVMultiPlane, PIVSnapshot


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    logger.setLevel(level.upper())
    _file_handler.setLevel(level.upper())
    _stream_handler.setLevel(level.upper())


__all__ = ['set_loglevel', 'cfx2hdf', 'pivview',
           'PIVSnapshot', 'PIVPlane', 'PIVMultiPlane']
