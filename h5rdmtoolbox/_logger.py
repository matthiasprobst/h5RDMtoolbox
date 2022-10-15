import logging
import pathlib
from logging.handlers import RotatingFileHandler
from typing import Tuple

import appdirs

DEFAULT_LOGGING_LEVEL = logging.INFO


def create_package_logger(name) -> Tuple[logging.Logger, RotatingFileHandler, logging.StreamHandler]:
    """Create logger based on name"""
    _logdir = appdirs.user_log_dir(name)
    _log = pathlib.Path(_logdir)  # Currently, this is unversioned

    if _log.exists():
        _logFolderMsg = f'{name} log folder available: {_logdir}'
    else:
        pathlib.Path.mkdir(_log, parents=True)
        _logFolderMsg = f'{name} log folder created at {_logdir}'

    # Initialize logger, set high level to prevent ipython debugs. File level is
    # set below
    _logger = logging.getLogger(name)
    _logger.setLevel(DEFAULT_LOGGING_LEVEL)

    _formatter = logging.Formatter(
        '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d_%H:%M:%S')

    _file_handler = RotatingFileHandler(_log / f'{name}.log', maxBytes=int(5e6), backupCount=2)
    _file_handler.setLevel(DEFAULT_LOGGING_LEVEL)
    _file_handler.setFormatter(_formatter)

    _stream_handler = logging.StreamHandler()
    _stream_handler.setLevel(DEFAULT_LOGGING_LEVEL)
    _stream_handler.setFormatter(_formatter)

    _logger.addHandler(_file_handler)
    _logger.addHandler(_stream_handler)

    # Log messages collected above
    _logger.debug(_logFolderMsg)

    return _logger, _file_handler, _stream_handler


logger, file_handler, stream_handler = create_package_logger(name='h5rdmtoolbox')
