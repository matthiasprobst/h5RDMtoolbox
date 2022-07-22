import unittest

import xarray as xr

from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.standard_names import StandardNameConvention
from h5rdmtoolbox.h5wrapper import H5Flow
from h5rdmtoolbox.h5wrapper.h5flow import XRVelocityDataset, VectorDataset


class TestH5Flow(unittest.TestCase):

    def test_vector(self):
        with tutorial.get_H5PIV('minimal_flow', mode='r') as h5:
            vec = h5.get_vector(names=('u', 'v'))
            self.assertIsInstance(vec, VectorDataset)
            vecarr = vec[:, :]
            self.assertIsInstance(vecarr, xr.Dataset)

            self.assertIsInstance(h5.VelocityVector, VectorDataset)
            vel = h5.VelocityVector[0, 0, :, :]
            self.assertIsInstance(vel, xr.Dataset)
            self.assertIsInstance(h5.VelocityVector('x_velocity', 'y_velocity'), VectorDataset)
            vel = h5.VelocityVector('x_velocity', 'y_velocity')[0, 0, :, :]
            print(vel)
            self.assertIsInstance(vel, xr.Dataset)
            with self.assertRaises(ValueError):
                h5.VelocityVector('x_velocity')

    def test_vector2(self):
        with tutorial.get_H5PIV('minimal_flow', mode='r') as h5:
            vel = h5.VelocityVector('x_velocity', 'y_velocity')[0, 0, :, :]
            self.assertEqual(('u', 'v'), vel.vector_vars)
            vel.compute_magnitude()
            self.assertTrue('magnitude' in vel)
            self.assertEqual(vel['magnitude'].attrs['standard_name'], 'magnitude_of_velocity')

    def test_convention(self):
        self.assertTrue(H5Flow.Layout.filename.exists())
        self.assertEqual(H5Flow.Layout.filename.stem, 'H5Flow')
        with H5Flow() as h5:
            self.assertIsInstance(h5.sn_convention, StandardNameConvention)
            self.assertEqual(h5.sn_convention.version, 1)
            self.assertEqual(h5.sn_convention.name, 'Fluid_Standard_Name')

    def test_VelocityDataset(self):
        with H5Flow() as h5:
            u = h5.create_dataset('u', shape=(10, 20), long_name='x velocity')
            v = h5.create_dataset('v', shape=(10, 20), long_name='y velocity')
            with self.assertRaises(NameError):
                h5.VelocityVector[:, :]

            with self.assertRaises(NameError):
                h5.VelocityVector('u', 'v')[:, :]

            vel0 = h5.VelocityVector(names=('u', 'v'))[:, :]
            self.assertIsInstance(vel0, XRVelocityDataset)
            self.assertEqual(vel0.u.shape, (10, 20))
            u.attrs['standard_name'] = 'x_velocity'
            v.attrs['standard_name'] = 'y_velocity'

            vel1 = h5.VelocityVector[:, :]
            self.assertIsInstance(vel1, XRVelocityDataset)
            self.assertEqual(vel1.u.shape, (10, 20))

            u = h5.create_dataset('grp/u', shape=(10, 20), long_name='x velocity')
            v = h5.create_dataset('grp/v', shape=(10, 20), long_name='y velocity')
            vel2 = h5['grp'].VelocityVector(names=('u', 'v'))[:, :]
            self.assertIsInstance(vel2, XRVelocityDataset)
            self.assertEqual(vel2.u.shape, (10, 20))

            u.attrs['standard_name'] = 'x_velocity'
            v.attrs['standard_name'] = 'y_velocity'
            vel3 = h5['grp'].VelocityVector[:, :]
            self.assertIsInstance(vel3, XRVelocityDataset)
            self.assertEqual(vel3.u.shape, (10, 20))

            u = h5.create_dataset('grp/u2', shape=(10, 20), long_name='x velocity')
            v = h5.create_dataset('grp/v2', shape=(10, 20), long_name='y velocity')
            u.attrs['standard_name'] = 'x_velocity'
            v.attrs['standard_name'] = 'y_velocity'
            with self.assertRaises(NameError):
                vel4 = h5['grp'].VelocityVector[:, :]

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
