import unittest

import h5rdmtoolbox as h5tbx


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use('h5py')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use('tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('tbx2')
