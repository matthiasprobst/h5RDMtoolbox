import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.extensions import normalize, vector, magnitude


class TestExtension(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_HDFXrDataset(self):
        with h5tbx.File() as h5:
            u = h5.create_dataset('u', data=np.arange(10, 20))
            v = h5.create_dataset('v', data=np.arange(10, 100))
            v2 = h5.create_dataset('v2', data=np.arange(10, 20))
            with self.assertRaises(ValueError):
                vector.HDFXrDataset(u=u, v=v)
            vel = vector.HDFXrDataset(u=u, v=v2)
            self.assertEqual(vel.data_vars, ['u', 'v'])
            self.assertEqual(vel.shape, (10,))
            self.assertIsInstance(vel[:], xr.Dataset)

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
            for i in range(3):
                self.assertEqual(float(vec.magnitude_of_uu_vv[i].values),
                                 np.sqrt(float(vec.uu[i].values) ** 2 + float(vec.vv[i].values) ** 2))

            vec.magnitude.compute_from('uu', 'vv', name='speed', inplace=True)
            self.assertTrue('speed' in vec.data_vars)
            with self.assertRaises(KeyError):
                vec.magnitude.compute_from('uu', 'vv', name='speed', inplace=True)
            vec.magnitude.compute_from('uu', 'vv', name='speed2', inplace=True, overwrite=True, attrs={'test': 1})
            self.assertEqual(vec.speed2.attrs['test'], 1)
            vec2 = vec.magnitude.compute_from('uu', 'vv', name='speed2', inplace=False, overwrite=True,
                                              attrs={'test': 1})
            self.assertEqual(vec2.attrs['test'], 1)
            self.assertIsInstance(vec2, xr.DataArray)

    def test_norm_one_for_all_with_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(L='3 m')
            self.assertIn('x / L', newu.dims)
            self.assertIn('y / L', newu.dims)
            self.assertIn('x / L', newu.coords)
            self.assertIn('y / L', newu.coords)
            self.assertEqual(newu['x / L'].attrs['units'], '1 / meter')

    def test_norm_one_for_all_without_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(L='3')
            self.assertIn('x / L', newu.dims)
            self.assertIn('y / L', newu.dims)
            self.assertIn('x / L', newu.coords)
            self.assertIn('y / L', newu.coords)
            self.assertEqual(newu['x / L'].attrs['units'], 'dimensionless')

    def test_norm_only_one_without_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(x='3')
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu['x'][0].values, 1 / 3)
            self.assertEqual(newu['x'][1].values, 2 / 3)
            self.assertEqual(newu['x'][2].values, 3 / 3)
            self.assertEqual(newu['y'][0].values, 1)
            self.assertEqual(newu['y'][1].values, 2)
            self.assertEqual(newu['y'][2].values, 3)
            self.assertEqual(newu['x'].attrs['units'], 'dimensionless')
            self.assertEqual(newu['y'].attrs['units'], '')

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(y='3')
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu['y'][0].values, 1 / 3)
            self.assertEqual(newu['y'][1].values, 2 / 3)
            self.assertEqual(newu['y'][2].values, 3 / 3)
            self.assertEqual(newu['y'][3].values, 4 / 3)
            self.assertEqual(newu['x'][0].values, 1)
            self.assertEqual(newu['x'][1].values, 2)
            self.assertEqual(newu['x'][2].values, 3)
            self.assertEqual(newu['y'].attrs['units'], 'dimensionless')
            self.assertEqual(newu['x'].attrs['units'], '')

    def test_norm_coords_without_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(y='3', x='4')
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu['y'][0].values, 1 / 3)
            self.assertEqual(newu['y'][1].values, 2 / 3)
            self.assertEqual(newu['y'][2].values, 3 / 3)
            self.assertEqual(newu['y'][3].values, 4 / 3)
            self.assertEqual(newu['x'][0].values, 1 / 4)
            self.assertEqual(newu['x'][1].values, 2 / 4)
            self.assertEqual(newu['x'][2].values, 3 / 4)
            self.assertEqual(newu['y'].attrs['units'], 'dimensionless')
            self.assertEqual(newu['x'].attrs['units'], 'dimensionless')

    def test_norm(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(x=3)
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'dimensionless')

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(x=3)
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'meter')
            self.assertEqual(newu.x[0].values, 1 / 3)
            self.assertEqual(newu.x[1].values, 2 / 3)
            self.assertEqual(newu.x[2].values, 3 / 3)
            self.assertEqual(newu.y[0].values, 1)
            self.assertEqual(newu.y[1].values, 2)
            self.assertEqual(newu.y[2].values, 3)
            self.assertEqual(newu.y[3].values, 4)

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(x=3)
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'meter')
            self.assertEqual(newu.x[0].values, 1 / 3)
            self.assertEqual(newu.x[1].values, 2 / 3)
            self.assertEqual(newu.x[2].values, 3 / 3)
            self.assertEqual(newu.y[0].values, 1)
            self.assertEqual(newu.y[1].values, 2)
            self.assertEqual(newu.y[2].values, 3)
            self.assertEqual(newu.y[3].values, 4)

    def test_norm2(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(x=xr.DataArray(3, attrs={'units': 'mm'}))
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'dimensionless')
            self.assertEqual(newu.x[0].values, 1 / 3 * 1000)
            self.assertEqual(newu.x[1].values, 2 / 3 * 1000)
            self.assertEqual(newu.x[2].values, 3 / 3 * 1000)
            self.assertEqual(newu.y[0].values, 1)
            self.assertEqual(newu.y[1].values, 2)
            self.assertEqual(newu.y[2].values, 3)
            self.assertEqual(newu.y[3].values, 4)

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords(3)
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'meter')
            self.assertEqual(newu.x[0].values, 1 / 3)
            self.assertEqual(newu.x[1].values, 2 / 3)
            self.assertEqual(newu.x[2].values, 3 / 3)
            self.assertEqual(newu.y[0].values, 1 / 3)
            self.assertEqual(newu.y[1].values, 2 / 3)
            self.assertEqual(newu.y[2].values, 3 / 3)
            self.assertEqual(newu.y[3].values, 4 / 3)

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords('3 m')
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'dimensionless')
            self.assertEqual(newu.x[0].values, 1 / 3)
            self.assertEqual(newu.x[1].values, 2 / 3)
            self.assertEqual(newu.x[2].values, 3 / 3)
            self.assertEqual(newu.y[0].values, 1 / 3)
            self.assertEqual(newu.y[1].values, 2 / 3)
            self.assertEqual(newu.y[2].values, 3 / 3)
            self.assertEqual(newu.y[3].values, 4 / 3)

        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            newu = h5.u[:].normalize.coords('3 mm')
            self.assertIn('x', newu.dims)
            self.assertIn('y', newu.dims)
            self.assertIn('x', newu.coords)
            self.assertIn('y', newu.coords)
            self.assertEqual(newu.x.attrs['units'], 'dimensionless')
            self.assertEqual(newu.x[0].values, 1 / 3 * 1000)
            self.assertEqual(newu.x[1].values, 2 / 3 * 1000)
            self.assertEqual(newu.x[2].values, 3 / 3 * 1000)
            self.assertEqual(newu.y[0].values, 1 / 3 * 1000)
            self.assertEqual(newu.y[1].values, 2 / 3 * 1000)
            self.assertEqual(newu.y[2].values, 3 / 3 * 1000)
            self.assertEqual(newu.y[3].values, 4 / 3 * 1000)
