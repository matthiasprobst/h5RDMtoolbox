"""
Subpackage h5wrapper:
Contains wrapper classes
"""

from ._logger import logger, _file_handler, _stream_handler
from .h5file import H5File
from .h5flow import H5Flow
from .h5piv import H5PIV


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    logger.setLevel(level.upper())
    _file_handler.setLevel(level.upper())
    _stream_handler.setLevel(level.upper())


def build_all_layoutfiles():
    """builds layout files of all wrapper classes in the user directory"""
    all_wrapperclasses = (H5File, H5Flow, H5PIV)
    for wrapperclass in all_wrapperclasses:
        wrapperclass.Layout.write()


build_all_layoutfiles()


def open(filename, mode='r', **kwargs):
    """opens an HDF file and returns an opened instance of the identified wrapper class which
    has been writng to the file the last time it was opened."""
    from h5py import File
    with File(filename) as h5:
        _class = h5.attrs.get('__wrcls__')
    if _class is None:
        return H5File(filename, mode=mode, **kwargs)
    if _class.lower() == 'h5file':
        return H5File(filename, mode=mode, **kwargs)
    if _class.lower() == 'h5flow':
        return H5Flow(filename, mode=mode, **kwargs)
    if _class.lower() == 'h5piv':
        return H5PIV(filename, mode=mode, **kwargs)


__all__ = ['H5File', 'H5Flow', 'H5PIV', 'set_loglevel']
