import datetime
import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.extensions import normalize, vector, magnitude, units


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

    def test_normalize_issue_with_time_vector(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            now = datetime.datetime.now()
            h5.create_time_dataset('t',
                                   data=[now, now + datetime.timedelta(seconds=1), now + datetime.timedelta(seconds=2)],
                                   make_scale=True)
            u = h5.create_dataset('u', data=[-4, 10, 0], attach_scales=[('t', 'x'), ])

            with self.assertRaises(RuntimeError):
                u[()].normalize.coords(rename=True, L=5)
            unorm = u[()].normalize.coords(rename=True, x=dict(L=5))
            np.testing.assert_array_equal(unorm['x/L'].values, u[()].x.values / 5)
            np.testing.assert_array_equal(unorm.values, u[()].values)

    def test_norm_one_for_all_without_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))

            with self.assertRaises(TypeError):
                h5['u'][:].normalize(dict(L='3m'), rename=2)

            unorm = h5['u'][:].normalize({"L": '3m'}, rename=True)
            self.assertEqual(f'u{normalize.NORM_DELIMITER}L', unorm.name)
            self.assertEqual('1/m', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3)
            self.assertEqual(unorm.attrs['comment'], 'Normalized by L=3m')

            unorm = h5['u'][:].normalize(dict(L='3m', o=4.5), rename=True)
            self.assertEqual(f'u{normalize.NORM_DELIMITER}L{normalize.NORM_DELIMITER}o', unorm.name)
            self.assertEqual('1/m', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3 / 4.5)

            unorm = h5['u'][:].normalize(dict(L='3m', o=4.5), rename=False)
            self.assertEqual('u', unorm.name)
            self.assertEqual('1/m', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3 / 4.5)

            unorm = h5['v'][:].normalize(dict(L='3m', o=4.5), rename=True)
            self.assertEqual(f'v{normalize.NORM_DELIMITER}L{normalize.NORM_DELIMITER}o', unorm.name)
            self.assertEqual('1/m', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['v'][()].values / 3 / 4.5)

            u_xnorm = h5['u'][:].normalize.coords(dict(L='3m'), rename=True)
            self.assertEqual('u', u_xnorm.name)
            for coord in u_xnorm.coords:
                self.assertEqual(f'{normalize.NORM_DELIMITER}L', coord[-2:])
            self.assertEqual('', u_xnorm.attrs.get('units', ''))
            self.assertEqual('1/m', u_xnorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('1/m', u_xnorm[f'y{normalize.NORM_DELIMITER}L'].attrs['units'])

            u_xnorm = h5['u'][:].normalize.coords(dict(L='3m'), rename=False)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('', u_xnorm.attrs.get('units', ''))
            self.assertEqual('1/m', u_xnorm['x'].attrs['units'])
            self.assertEqual('1/m', u_xnorm['y'].attrs['units'])

            u_xnorm = h5['u'][:].normalize.coords(dict(x={'L': '3m'}), rename=False)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('', u_xnorm.attrs.get('units', ''))
            self.assertEqual('1/m', u_xnorm['x'].attrs['units'])
            self.assertEqual('', u_xnorm['y'].attrs.get('units', ''))

    def test_norm_one_for_all_with_unit(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'mm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'), attrs={'units': 'm/s'})
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'), attrs={'units': 'Pa'})

            unorm = h5['u'][:].normalize(dict(L='3m'), rename=True)
            self.assertEqual(f'u{normalize.NORM_DELIMITER}L', unorm.name)
            self.assertEqual('1/s', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3)

            unorm = h5['u'][:].normalize(dict(L='3m', o=4.5), rename=True)
            self.assertEqual(f'u{normalize.NORM_DELIMITER}L{normalize.NORM_DELIMITER}o', unorm.name)
            self.assertEqual('1/s', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3 / 4.5)

            unorm = h5['u'][:].normalize(dict(L='3m', o=4.5), rename=False)
            self.assertEqual('u', unorm.name)
            self.assertEqual('1/s', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['u'][()].values / 3 / 4.5)

            unorm = h5['v'][:].normalize(dict(L='3m', o=4.5), rename=True)
            self.assertEqual(f'v{normalize.NORM_DELIMITER}L{normalize.NORM_DELIMITER}o', unorm.name)
            self.assertEqual('Pa/m', unorm.attrs['units'])
            np.testing.assert_array_equal(unorm.values, h5['v'][()].values / 3 / 4.5)

            u_xnorm = h5['u'][:].normalize.coords(dict(L='3m'), rename=True)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            for coord in u_xnorm.coords:
                self.assertEqual(f'{normalize.NORM_DELIMITER}L', coord[-2:])
            self.assertEqual('', u_xnorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('mm/m', u_xnorm[f'y{normalize.NORM_DELIMITER}L'].attrs['units'])

            u_xnorm = h5['u'][:].normalize.coords(L='3m', rename=True)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            for coord in u_xnorm.coords:
                self.assertEqual(f'{normalize.NORM_DELIMITER}L', coord[-2:])
            self.assertEqual('', u_xnorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('mm/m', u_xnorm[f'y{normalize.NORM_DELIMITER}L'].attrs['units'])

            u_xnorm = h5['u'][:].normalize.coords(dict(L='3m'), rename=False)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            self.assertEqual('', u_xnorm['x'].attrs['units'])
            self.assertEqual('mm/m', u_xnorm['y'].attrs['units'])
            np.testing.assert_array_equal(u_xnorm['x'].values, h5['x'][()].values / 3)
            np.testing.assert_array_equal(u_xnorm['y'].values, h5['y'][()].values / 3)

            u_xnorm = h5['u'][:].normalize.coords({'x': {"L": '3m'}}, rename=False)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            self.assertEqual('', u_xnorm['x'].attrs['units'])
            self.assertEqual('mm', u_xnorm['y'].attrs.get('units', ''))

            u_xnorm = h5['u'][:].normalize.coords({'x': {"L": '3m'}}, rename=True)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual(f'x{normalize.NORM_DELIMITER}L', u_xnorm["x/L"].name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            self.assertEqual('', u_xnorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('mm', u_xnorm['y'].attrs.get('units', ''))

            u_xnorm = h5['u'][:].normalize.coords(x={"L": '3m'}, rename=True)
            self.assertEqual('u', u_xnorm.name)
            self.assertEqual(f'x{normalize.NORM_DELIMITER}L', u_xnorm["x/L"].name)
            self.assertEqual('m/s', u_xnorm.attrs.get('units', ''))
            self.assertEqual('', u_xnorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('mm', u_xnorm['y'].attrs.get('units', ''))

            u_xynorm = h5['u'][:].normalize.coords(x={"L": '3m'}, y=10, rename=True)
            self.assertEqual('u', u_xynorm.name)
            self.assertEqual(f'x{normalize.NORM_DELIMITER}L', u_xynorm["x/L"].name)
            self.assertEqual('y', u_xynorm.y.name)
            self.assertEqual('m/s', u_xynorm.attrs.get('units', ''))
            self.assertEqual('', u_xynorm[f'x{normalize.NORM_DELIMITER}L'].attrs['units'])
            self.assertEqual('mm', u_xynorm['y'].attrs.get('units', ''))
            self.assertEqual(u_xynorm.y[0], h5['u'][:].y[0] / 10)

    def test_units_to(self):
        with h5tbx.File(mode='w') as h5:
            ds = h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            y = h5.create_dataset('y', data=[1, 0, 1], attach_scale='x', attrs={'units': 'mm'})
            ds_cm = ds[()].to('cm')
            self.assertEqual('cm', ds_cm.attrs['units'])

            y_cm = y[()].to('cm')
            self.assertEqual('cm', y_cm.attrs['units'])

            y_xcm = y[()].to({'x': 'cm'})
            self.assertEqual('mm', y_xcm.attrs['units'])
            self.assertEqual('cm', y_xcm.x.attrs['units'])

            y_xcm = y[()].to(x='cm')
            self.assertEqual('mm', y_xcm.attrs['units'])
            self.assertEqual('cm', y_xcm.x.attrs['units'])
