import unittest

import h5rdmtoolbox as h5tbx


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use(h5tbx.get_config()['default_convention'])
        self.assertEqual(h5tbx.conventions.current_convention.name, h5tbx.get_config()['default_convention'])
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use('h5py')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use('h5tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('invalid_convention')
