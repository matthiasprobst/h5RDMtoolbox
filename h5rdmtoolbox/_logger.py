"""package-wide logger module"""
import appdirs
import logging
import pathlib
from logging.handlers import RotatingFileHandler

DEFAULT_LOGGING_LEVEL = logging.INFO


class ToolboxLogger(logging.Logger):
    """Wrapper class for logging.Logger to add a setLevel method"""

    def setLevel(self, level):
        """change the log level which displays on the console"""
        old_level = self.handlers[1].level
        self.handlers[1].setLevel(level)
        self.debug(f'changed logger level for {self.name} from {old_level} to {level}')


def create_tbx_logger(name, logdir=None) -> ToolboxLogger:
    """Create logger based on name"""
    if logdir is None:
        _logdir = pathlib.Path(appdirs.user_log_dir('h5rdmtoolbox'))
    else:
        _logdir = pathlib.Path(logdir)

    if _logdir.exists():
        _logFolderMsg = f'{name} log folder available: {_logdir}'
    else:
        pathlib.Path.mkdir(_logdir, parents=True)
        _logFolderMsg = f'{name} log folder created at {_logdir}'

    _logger = ToolboxLogger(logging.getLogger(name))

    _formatter = logging.Formatter(
        '%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d_%H:%M:%S')

    _file_handler = RotatingFileHandler(_logdir / f'{name}.log', maxBytes=int(5e6), backupCount=2)
    _file_handler.setLevel(logging.DEBUG)  # log everything to file!
    _file_handler.setFormatter(_formatter)

    _stream_handler = logging.StreamHandler()
    _stream_handler.setLevel(DEFAULT_LOGGING_LEVEL)
    _stream_handler.setFormatter(_formatter)

    _logger.addHandler(_file_handler)
    _logger.addHandler(_stream_handler)

    # Log messages collected above
    _logger.debug(_logFolderMsg)

    return _logger


# initialize loggers for all modules

loggers = {'h5rdmtoolbox': create_tbx_logger('h5rdmtoolbox'),
           'conventions': create_tbx_logger('h5rdmtoolbox.convention'),
           'wrapper': create_tbx_logger('h5rdmtoolbox.wrapper'),
           'database': create_tbx_logger('h5rdmtoolbox.database')}
