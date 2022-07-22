import logging
import unittest

from h5rdmtoolbox import set_loglevel

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
        for lname in ('h5rdmtoolbox.h5wrapper',
                      'h5rdmtoolbox.x2hdf',
                      'h5rdmtoolbox.h5database',
                      'h5rdmtoolbox.conventions'):
            logger = logging.getLogger(lname)
            self.assertEqual(lname, logger.name)
            for level in levels:
                set_loglevel(level)
                self.assertEqual(logger.level, levels[level])
