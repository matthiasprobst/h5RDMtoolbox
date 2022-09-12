import logging
import pathlib

import appdirs

name = __package__

_logdir = appdirs.user_log_dir(name)
_log = pathlib.Path(_logdir)  # Currently, this is unversioned

if not _log.exists():
    pathlib.Path.mkdir(_log, parents=True, exist_ok=False)
    _logFolderMsg = f'{name} log folder created at {_logdir}'
else:
    _logFolderMsg = f'f{name} log folder exist at {_logdir}'

# Initialize logger, set high level to prevent ipython debugs. File level is
# set below
DEFAULT_LOGGING_LEVEL = logging.INFO
logger = logging.getLogger(__package__)
logger.setLevel(DEFAULT_LOGGING_LEVEL)

_formatter = logging.Formatter(
    '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d_%H:%M:%S')

# Log messages collected above
logger.debug(_logFolderMsg)
