"""
Subpackage h5wrapper:
Contains wrapper classes
"""

from h5py import ExternalLink as H5pyExternalLink

from . import _logger
from .accessory import register_special_property, register_special_dataset
from .h5file import H5File
from .h5flow import H5Flow
from .h5piv import H5PIV


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    if isinstance(level, str):
        _logger.logger.setLevel(level.upper())
        _logger.file_handler.setLevel(level.upper())
        _logger.stream_handler.setLevel(level.upper())
    else:
        _logger.logger.setLevel(level)
        _logger.file_handler.setLevel(level)
        _logger.stream_handler.setLevel(level)


def open_wrapper(filename, mode='r', **kwargs):
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


class ExternalLink(H5pyExternalLink):
    """External Link wrapper class"""

    def __enter__(self):
        self._file = open_wrapper(self.filename)
        return self._file[self.path]

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()


__all__ = ['H5File', 'H5Flow', 'H5PIV', 'set_loglevel', 'open_wrapper']
