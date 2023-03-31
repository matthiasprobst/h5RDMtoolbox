import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.extensions import vector, magnitude


class TestExtension(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

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
            vec.magnitude.compute_from('uu', 'vv', inplace=True)
            self.assertTrue('magnitude_of_uu_vv' in vec.data_vars)
            vec.magnitude.compute_from('uu', 'vv', name='speed', inplace=True)
            self.assertTrue('speed' in vec.data_vars)
            with self.assertRaises(KeyError):
                vec.magnitude.compute_from('uu', 'vv', name='speed', inplace=True)
            vec.magnitude.compute_from('uu', 'vv', name='speed2', inplace=True, overwrite=True, attrs={'test': 1})
            self.assertEqual(vec.speed2.attrs['test'], 1)
            vec2 = vec.magnitude.compute_from('uu', 'vv', name='speed2', inplace=False, overwrite=True, attrs={'test': 1})
            self.assertEqual(vec2.attrs['test'], 1)
            self.assertIsInstance(vec2, xr.DataArray)
