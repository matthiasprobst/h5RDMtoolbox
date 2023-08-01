import unittest

from h5rdmtoolbox import loggers

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
        for logger in loggers.values():

            self.assertEqual(len(logger.handlers), 2)
            for level in levels:
                logger.setLevel(level)
                self.assertEqual(logger.handlers[1].level, levels[level])
