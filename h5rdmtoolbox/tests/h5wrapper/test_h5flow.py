import unittest

import numpy as np
import xarray as xr

from h5rdmtoolbox.conventions import StandardizedNameTable, StandardizedNameError
from h5rdmtoolbox.h5wrapper import H5Flow
from h5rdmtoolbox.h5wrapper.accessory import SpecialDataset
from h5rdmtoolbox.h5wrapper.h5flow import Device


class TestH5Flow(unittest.TestCase):

    def test_convention(self):
        self.assertTrue(H5Flow.Layout.filename.exists())
        self.assertEqual(H5Flow.Layout.filename.stem, 'H5Flow')
        with H5Flow() as h5:
            self.assertIsInstance(h5.standard_name_table, StandardizedNameTable)
            self.assertEqual(h5.standard_name_table.version_number, 1)
            self.assertEqual(h5.standard_name_table.name, 'fluid')
            self.assertEqual(h5.standard_name_table.versionname, 'fluid-v1')

    def test_VectorAccsessor(self):
        with H5Flow() as h5:
            h5.create_coordinates(x=np.linspace(0, 1, 20),
                                  y=np.linspace(0, 0.5, 10),
                                  z=np.linspace(-1, 1, 3),
                                  coords_unit='mm')
            h5.create_velocity_datasets(u=np.random.rand(3, 10, 20),
                                        v=np.random.rand(3, 10, 20),
                                        w=np.random.rand(3, 10, 20),
                                        dim_scales=('z', 'y', 'x'),
                                        units='mm/s')

            vel = h5.Vector(names=('u', 'v', 'w'))[0:1, :, :]
            u = vel.u
            self.assertIsInstance(h5.Vector(names=('u', 'v', 'w')), SpecialDataset)
            self.assertIsInstance(u, xr.DataArray)
            self.assertEqual(u.shape, (1, 10, 20))
            self.assertEqual(vel.v.shape, (1, 10, 20))
            self.assertEqual(vel.v.name, 'v')
            self.assertEqual(vel.w.shape, (1, 10, 20))
            self.assertEqual(vel.w.name, 'w')

    def test_VelocityDataset(self):
        with H5Flow() as h5:
            u = h5.create_dataset('u', shape=(10, 20), standard_name='x_velocity', units='m/s')
            v = h5.create_dataset('v', shape=(10, 20), standard_name='y_velocity', units='m/s')
            u[:, :] = np.random.random((10, 20))
            v[:, :] = np.random.random((10, 20))

            vel = h5.VelocityVector[2:4, 5:10]
            vel.compute_magnitude()

    def test_Layout(self):
        self.assertTrue(H5Flow.Layout.filename.exists())
        self.assertEqual(H5Flow.Layout.filename.stem, 'H5Flow')
        H5Flow.Layout.write()
        H5Flow.Layout.sdump()
        with H5Flow() as h5:
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 5)
            h5.title = 'my title'
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 4)

            # check for standard anmes
            # CGNS convention:
            # create dataset with cf convention:
            ds = h5.create_dataset('x', data=1, units='m', standard_name='x_coordinate')
            with self.assertRaises(StandardizedNameError):
                ds.attrs['standard_name'] = 'CoordinateX'
            h5.check()
            del h5['x']

            # generatig wrong x coordinate dimension:
            h5.create_dataset('x', shape=(2, 1), units='m', standard_name='x_coordinate')
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 4)

            del h5['x']
            # generatig correct x coordinate dimension:
            h5.create_dataset('x', shape=(12,), units='m', standard_name='x_coordinate')
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 3)

            del h5['x']
            # use [mm] for units. must be accepted:
            h5.create_dataset('x', shape=(12,), units='mm', standard_name='x_coordinate')
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 3)

            # use [kg] for units. must be NOT accepted:
            h5['x'].attrs['units'] = 'kg'
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 4)

    def test_device(self):
        with H5Flow() as h5:
            ds = h5.create_dataset('pressure', data=[1, 2, 3], standard_name='pressure', units='Pa')
            grp = h5.create_group('devices')
            ps_grp = grp.create_group('PressureSensor')
            ps_grp.attrs['manufacturer'] = 'unknown'
            ps_grp.create_dataset('x', data=0, units='m', standard_name='x_coordinate')
            ps_grp.create_dataset('y', data=1, units='m', standard_name='y_coordinate')
            ps_grp.create_dataset('z', data=0, units='m', standard_name='z_coordinate')
            ds.assign_device(ps_grp)

            self.assertIsInstance(ds.device.x, xr.DataArray)
            self.assertEqual(ds.device.x, 0)
            self.assertEqual(ds.device.y, 1)
            self.assertEqual(ds.device.x, 0)
            h5.sdump()

        p_sensor = Device('PressureSensor', manufacturer='unknown',
                          x=(0, dict(units='m', standard_name='x_coordinate')),
                          y=(0, dict(units='m', standard_name='y_coordinate')),
                          z=(0, dict(units='m', standard_name='z_coordinate')))
        p_sensor
        with H5Flow() as h5:
            ds = h5.create_dataset('pressure', data=np.random.random(100), units='Pa', standard_name='pressure')
            ds.device = p_sensor

        with H5Flow() as h5:
            devices_grp = h5.create_group('devices')
            sensor_grp = p_sensor.to_hdf_group(devices_grp)

            ds = h5.create_dataset('pressure', data=np.random.random(100), units='Pa', standard_name='pressure',
                                   device=sensor_grp)
            ds.device = sensor_grp
