import unittest

from h5rdmtoolbox import logger as core_logger
from h5rdmtoolbox.conventions import logger as conventions_logger
from h5rdmtoolbox.wrapper import logger as wrapper_logger

levels = dict(
    CRITICAL=50,
    FATAL=50,
    ERROR=40,
    WARNING=30,
    WARN=30,
    INFO=20,
    DEBUG=10,
    NOTSET=0,
)


class TestLogger(unittest.TestCase):

    def test_setlogger(self):
        for logger in (core_logger, wrapper_logger, conventions_logger):
            orig_level = logger.level

            self.assertEqual(len(logger.handlers), 2)
            for level in levels:
                logger.setLevel(level)
                self.assertEqual(logger.handlers[1].level, levels[level])

            logger.setLevel(orig_level)
            self.assertEqual(logger.level, orig_level)
