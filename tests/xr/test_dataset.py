"""Testing common funcitonality across all wrapper classs"""

import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox
from h5rdmtoolbox.xr.dataset import HDFXrDataset


class TestDataset(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        h5rdmtoolbox.use('default')

    def test_HDFXrDataset(self):
        with h5rdmtoolbox.File() as h5:
            u = h5.create_dataset('u', data=np.arange(10, 20))
            v = h5.create_dataset('v', data=np.arange(10, 100))
            v2 = h5.create_dataset('v2', data=np.arange(10, 20))
            with self.assertRaises(ValueError):
                HDFXrDataset(u=u, v=v)
            vel = HDFXrDataset(u=u, v=v2)
            self.assertEqual(vel.data_vars, ['u', 'v'])
            self.assertEqual(vel.shape, (10,))
            self.assertIsInstance(vel[:], xr.Dataset)
