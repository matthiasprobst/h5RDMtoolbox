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

    def test_from_zenodo(self):
        with self.assertRaises(ValueError):
            cv = h5tbx.conventions.from_zenodo(doi=8158764)
        with self.assertRaises(ValueError):
            cv = h5tbx.conventions.from_zenodo(doi=1826462820292)
