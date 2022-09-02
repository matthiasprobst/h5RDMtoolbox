import unittest

import h5rdmtoolbox as h5tbx


class TestVersion(unittest.TestCase):
    def test_version(self):
        self.assertEqual(h5tbx.__version__, '0.1.12')
