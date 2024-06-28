import datetime
import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.extensions import normalize, vector, magnitude, units, onto


class TestExtension(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_onto(self):
        with h5tbx.File() as h5:
            h5.onto.create_person(orcid_id='https://orcid.org/0000-0001-8729-0482',
                                  first_name='Matthias',
                                  last_name='Probst')
            self.assertEqual(h5['Matthias_Probst'].attrs['orcid_id'], 'https://orcid.org/0000-0001-8729-0482')
            self.assertEqual(h5['Matthias_Probst'].attrs['first_name'], 'Matthias')
            self.assertEqual(h5['Matthias_Probst'].attrs['last_name'], 'Probst')
            self.assertEqual(h5['Matthias_Probst'].rdf.subject, 'https://orcid.org/0000-0001-8729-0482')

            h5.dumps()

    def test_Magnitude(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True, attrs={'units': 'm'})
            h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
            mag_interface = h5.Magnitude('u', 'v')
            self.assertIsInstance(mag_interface.datasets, dict)
            mag = mag_interface[()]
            self.assertEqual(mag.name, 'magnitude_of_u_and_v')
            self.assertEqual(float(mag[0, 0]),
                             float(np.sqrt(h5['u'][0, 0] ** 2 + h5['v'][0, 0] ** 2)))
            self.assertEqual(float(mag[1, 0]),
                             float(np.sqrt(h5['u'][1, 0] ** 2 + h5['v'][1, 0] ** 2)))
            self.assertEqual(float(mag[0, 1]),
                             float(np.sqrt(h5['u'][0, 1] ** 2 + h5['v'][0, 1] ** 2)))
            self.assertEqual(float(mag[3, 2]),
                             float(np.sqrt(h5['u'][3, 2] ** 2 + h5['v'][3, 2] ** 2)))

            mag_interface = h5.Magnitude('u', 'v', name='uv')
            mag = mag_interface[()]
            self.assertEqual(mag.name, 'uv')

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

            vec = h5.Vector(uu='u', vv='v')[:]
            self.assertListEqual(list(vec.data_vars), ['uu', 'vv'])
            self.assertEqual(vec['uu'][0], 1)
            self.assertEqual(vec['vv'][0], 2)

            vec = h5.Vector(u='u', v='v').isel(dim_0=slice(None, None, None), dim_1=slice(None, None, None))
            self.assertIsInstance(vec, xr.Dataset)
            self.assertTrue('u' in vec.data_vars)
            self.assertTrue('v' in vec.data_vars)
            self.assertEqual(vec['u'][0], 1)
            self.assertEqual(vec['v'][0], 2)

            with self.assertRaises(KeyError):
                h5.Vector(u='u', v='v').sel(dim_0=5, dim_1=2)

    def test_normalize_issue_with_time_vector(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            now = datetime.datetime.now()
            h5.create_time_dataset('t',
                                   data=[now, now + datetime.timedelta(seconds=1), now + datetime.timedelta(seconds=2)],
                                   time_format='iso',
                                   make_scale=True)
            u = h5.create_dataset('u', data=[-4, 10, 0], attach_scales=[('x', 't'), ],
                                  attrs=dict(units='m/s'))

            with self.assertRaises(AssertionError):
                u.normalize(10)

            with self.assertRaises(TypeError):
                u.normalize(ref={'t': 10})[()]

            unorm = u.normalize(ref=10)[()]
            np.testing.assert_almost_equal(unorm.values, u.values[()] / 10)
            self.assertEqual(unorm.units, 'm/s')
            self.assertEqual(unorm.name, 'u/ref')

            with self.assertRaises(TypeError):
                uxnorm = u.normalize(ref=10, name='uxnorm').x(xref={'t': 10})[()]
            uxnorm = u.normalize(ref=10, name='uxnorm').x(xref=10)[()]
            self.assertEqual(uxnorm.name, 'uxnorm')
            np.testing.assert_almost_equal(uxnorm.values, u.values[()] / 10)
            np.testing.assert_almost_equal(uxnorm['x/xref'].values, h5.x.values[()] / 10)
            self.assertEqual(uxnorm.units, 'm/s')

            uxnorm = u.normalize(ref=10, name='uxnorm').x(xref=10).isel(x=slice(None, None, None))
            np.testing.assert_almost_equal(uxnorm.values, u.values[()] / 10)
            np.testing.assert_almost_equal(uxnorm['x/xref'].values, h5.x.values[()] / 10)

            uxnorm = u.normalize(ref=10, name='uxnorm').x(xref=10).sel(x=[1.1, 2.1, 3.1], method='nearest')
            np.testing.assert_almost_equal(uxnorm.values, u.values[()] / 10)
            np.testing.assert_almost_equal(uxnorm['x/xref'].values, h5.x.values[()] / 10)

            uxnorm = u.normalize(ref='10 m/s').x(xref='10 m', name='xnorm')[()]
            np.testing.assert_almost_equal(uxnorm.values, u.values[()] / 10)
            np.testing.assert_almost_equal(uxnorm['xnorm'].values, h5.x.values[()] / 10)
            self.assertEqual(uxnorm['xnorm'].units, '1/m')
            self.assertEqual(uxnorm.units, '')

    def test_units_to(self):
        with h5tbx.File(mode='w') as h5:
            ds = h5.create_dataset('x', data=[1, 2, 3], make_scale=True, attrs={'units': 'm'})
            y = h5.create_dataset('y', data=[1, 0, 1], attach_scale='x', attrs={'units': 'mm'})
            ds_cm = ds.to_units('cm')[()]
            self.assertEqual('cm', ds_cm.attrs['units'])

            y_cm = y.to_units('cm')[()]
            self.assertEqual('cm', y_cm.attrs['units'])

            y_xcm = y.to_units({'x': 'cm'})[()]
            self.assertEqual('mm', y_xcm.attrs['units'])
            self.assertEqual('cm', y_xcm.x.attrs['units'])

            y_xcm = y.to_units(x='cm')[()]
            self.assertEqual('mm', y_xcm.attrs['units'])
            self.assertEqual('cm', y_xcm.x.attrs['units'])
