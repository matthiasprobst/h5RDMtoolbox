import matplotlib.pyplot as plt
import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions.standard_names import HDF5StandardNameInterface


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        cv = h5tbx.conventions.from_zenodo(doi=8357399)
        cv.properties[h5tbx.File]['data_type'].make_optional()
        cv.properties[h5tbx.File]['contact'].make_optional()
        h5tbx.use(cv)

    def tearDown(self) -> None:
        h5tbx.use(None)

    def assertUnitEqual(self, unit1, unit2):
        return h5tbx.get_ureg().Unit(unit1), h5tbx.get_ureg().Unit(unit2)

    def test_interface_without_coords(self):
        with h5tbx.File(contact=h5tbx.__author_orcid__) as h5:
            h5.create_dataset('x', data=[-4, 1, 3, 5, 10],
                              standard_name='x_coordinate',
                              units='m')
            h5.create_dataset('y', data=[10, 20, 30],
                              standard_name='y_coordinate',
                              units='m')
            h5.create_dataset('u', data=np.random.rand(3, 5),
                              standard_name='x_velocity',
                              units='m/s')
            h5.create_dataset('v', data=np.random.rand(3, 5),
                              standard_name='y_velocity',
                              units='m/s')
            h5.create_dataset('dudx', data=np.random.rand(3, 5),
                              standard_name='derivative_of_x_velocity_wrt_x_coordinate',
                              units='1/s')

        h5sni = HDF5StandardNameInterface.from_hdf(h5.hdf_filename)
        self.assertListEqual(sorted(['x_velocity',
                                     'y_velocity',
                                     'x_coordinate',
                                     'y_coordinate',
                                     'derivative_of_x_velocity_wrt_x_coordinate']),
                             sorted(h5sni.standard_names))
        mag = h5sni.velocity.magnitude()
        self.assertIsInstance(mag, xr.DataArray)
        self.assertUnitEqual(mag.units, 'm/s')

        plt.figure()
        h5sni.velocity.get('x', 'y').plot()
        plt.close()
        plt.figure()
        h5sni.velocity.get('x', 'y').plot.contourf()
        h5sni.velocity.get('x', 'y').plot.quiver()
        plt.close()

    def test_StandardCoordinate(self):
        with h5tbx.File(contact=h5tbx.__author_orcid__) as h5:
            h5.create_dataset('x', data=[-4, 1, 3, 5, 10],
                              standard_name='x_coordinate',
                              units='m', make_scale=True)
            h5.create_dataset('y', data=[10, 20, 30],
                              standard_name='y_coordinate',
                              units='m', make_scale=True)
            h5.create_dataset('u', data=np.random.rand(3, 5),
                              standard_name='x_velocity',
                              units='m/s',
                              attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.rand(3, 5),
                              standard_name='y_velocity',
                              units='m/s',
                              attach_scales=('y', 'x'))
            h5.create_dataset('grp/v', data=np.random.rand(3, 5),
                              standard_name='y_velocity',
                              units='m/s',
                              attach_scales=('y', 'x'))
        h5sni = HDF5StandardNameInterface.from_hdf(h5.hdf_filename)
        for c in h5sni.coordinate:
            self.assertIsInstance(c, h5tbx.database.lazy.LDataset)
        self.assertEqual(h5sni.coordinate.x, h5sni.coordinate[0])
        self.assertEqual(h5sni.coordinate.y, h5sni.coordinate[1])
        self.assertDictEqual({'x': 5, 'y': 3}, h5sni.coordinate.shape)
        self.assertEqual(2, h5sni.velocity.ndim)

    def test_interface_with_coords(self):
        with h5tbx.File(contact=h5tbx.__author_orcid__) as h5:
            h5.create_dataset('x', data=[-4, 1, 3, 5, 10],
                              standard_name='x_coordinate',
                              units='m', make_scale=True)
            h5.create_dataset('y', data=[10, 20, 30],
                              standard_name='y_coordinate',
                              units='m', make_scale=True)
            h5.create_dataset('u', data=np.random.rand(3, 5),
                              standard_name='x_velocity',
                              units='m/s',
                              attach_scales=('y', 'x'))
            h5.create_dataset('v', data=np.random.rand(3, 5),
                              standard_name='y_velocity',
                              units='m/s',
                              attach_scales=('y', 'x'))
            h5.create_dataset('dudx', data=np.random.rand(3, 5),
                              standard_name='derivative_of_x_velocity_wrt_x_coordinate',
                              units='1/s')

        h5sni = HDF5StandardNameInterface.from_hdf(h5.hdf_filename)
        self.assertListEqual(sorted(['x_velocity',
                                     'y_velocity',
                                     'x_coordinate',
                                     'y_coordinate',
                                     'derivative_of_x_velocity_wrt_x_coordinate']),
                             sorted(h5sni.standard_names))
        mag = h5sni.velocity.magnitude()
        self.assertIsInstance(mag, xr.DataArray)
        self.assertUnitEqual(mag.units, 'm/s')

        plt.figure()
        h5sni.velocity.get('x', 'y').plot()
        h5sni.velocity.get('x', 'y').plot.quiver()
        plt.close()

        ds = h5sni.velocity.get('x', 'y').get_xrdataset()
        self.assertIn('x_velocity', ds)
        self.assertIn('y_velocity', ds)
        self.assertIn('x', ds)
        self.assertIn('y', ds)
        self.assertIn('x', ds.coords)
        self.assertIn('y', ds.coords)
