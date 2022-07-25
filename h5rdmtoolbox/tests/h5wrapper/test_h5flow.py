import unittest

import numpy as np

from h5rdmtoolbox.conventions.standard_names import StandardNameConvention
from h5rdmtoolbox.h5wrapper import H5Flow


# from h5rdmtoolbox.h5wrapper.h5flow import XRVelocityDataset, VectorInterface


class TestH5Flow(unittest.TestCase):

    def test_convention(self):
        self.assertTrue(H5Flow.Layout.filename.exists())
        self.assertEqual(H5Flow.Layout.filename.stem, 'H5Flow')
        with H5Flow() as h5:
            self.assertIsInstance(h5.sn_convention, StandardNameConvention)
            self.assertEqual(h5.sn_convention.version, 1)
            self.assertEqual(h5.sn_convention.name, 'Fluid_Standard_Name')

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
