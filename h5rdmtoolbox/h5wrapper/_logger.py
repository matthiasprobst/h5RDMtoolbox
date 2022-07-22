import logging
import pathlib
from logging.handlers import RotatingFileHandler

import appdirs

name = __package__

_logdir = appdirs.user_log_dir(name)
_log = pathlib.Path(_logdir)  # Currently, this is unversioned

try:
    pathlib.Path.mkdir(_log, parents=True)
    _logFolderMsg = f'{name} log folder created at {_logdir}'
except FileExistsError:
    _logFolderMsg = f'{name} log folder available: {_logdir}'

# Initialize logger, set high level to prevent ipython debugs. File level is
# set below
DEFAULT_LOGGING_LEVEL = logging.INFO
logger = logging.getLogger(__package__)
logger.setLevel(DEFAULT_LOGGING_LEVEL)

_formatter = logging.Formatter(
    '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d_%H:%M:%S')

_file_handler = RotatingFileHandler(_log / f'{name}.log', maxBytes=int(5e6), backupCount=2)
_file_handler.setLevel(DEFAULT_LOGGING_LEVEL)
_file_handler.setFormatter(_formatter)

_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(DEFAULT_LOGGING_LEVEL)
_stream_handler.setFormatter(_formatter)

logger.addHandler(_file_handler)
logger.addHandler(_stream_handler)

# Log messages collected above
logger.debug(_logFolderMsg)

# other loggers:
# ---- piv uncertainty
piv_uncertainty_logger = logging.getLogger('piv_uncertainty')
_uncertainty_file_handler = RotatingFileHandler(_log / 'piv_uncertainty.log', maxBytes=int(5e6), backupCount=2)
_uncertainty_file_handler.setLevel(DEFAULT_LOGGING_LEVEL)
_uncertainty_file_handler.setFormatter(_formatter)
piv_uncertainty_logger.addHandler(_uncertainty_file_handler)
piv_uncertainty_logger.addHandler(_stream_handler)