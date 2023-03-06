import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.wrapper import accessory


class TestAccessory(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use('default')

    def test_Vector(self):
        """Test the Vector special dataset"""
        with h5tbx.File() as h5:
            h5.create_dataset('u', data=[1, 2, 3])
            h5.create_dataset('v', data=[2, 2, 2])

            self.assertIsInstance(h5.Vector('u', 'v')[:], xr.Dataset)
            vec = h5.Vector(h5['u'], h5['v'])[:]
            self.assertIsInstance(vec, xr.Dataset)
            self.assertTrue('u' in vec.data_vars)
            self.assertTrue('v' in vec.data_vars)
            vec = h5.Vector(uu=h5['u'], vv=h5['v'])[:]
            self.assertIsInstance(vec, xr.Dataset)
            self.assertTrue('uu' in vec.data_vars)
            self.assertTrue('vv' in vec.data_vars)
            with self.assertRaises(ValueError):
                h5.Vector('u', 'v', u='u')
            with self.assertRaises(TypeError):
                h5.Vector('u', 6.5)
            with self.assertRaises(TypeError):
                h5.Vector(u='u', v=6.5)
