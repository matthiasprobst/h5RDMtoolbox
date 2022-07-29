import unittest

import numpy as np
import xarray as xr

from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions import StandardizedNameTable
from h5rdmtoolbox.h5wrapper import H5PIV


def my_uncertainty_method(uds, imgA, imgB):
    """
    Dummy uncertainty method for this tutorial.
    Returns the same dataset but with added uncertainties

    Parameters
    ----------
    uds: XRUncertaintyDataset
        The uncertainty dataset containing, x, y, ix, iy, dx, dy, ...
    imgA: np.ndarray
        2d PIV image A. Will not be touch in this example
    imgB: np.ndarray
        2d PIV image B. Will not be touch in this example

    Returns
    -------
    uds: XRUncertaintyDataset
    """
    xerr = 0.05
    yerr = 0.075
    udx = np.abs(uds.dx) * xerr
    uds['udx'] = xr.DataArray(dims=uds.dx.dims, data=udx,
                              attrs={'standard_name': f'uncertainty_of_{uds.dx.standard_name}',
                                     'units': 'pixel',
                                     'piv_uncertainty_method': 'my_uncertainty_method'})
    udy = np.abs(uds.dy) * yerr
    uds['udy'] = xr.DataArray(dims=uds.dy.dims, data=udy,
                              attrs={'standard_name': f'uncertainty_of_{uds.dy.standard_name}',
                                     'units': 'pixel',
                                     'piv_uncertainty_method': 'my_uncertainty_method'})
    return uds


class TestH5PIV(unittest.TestCase):

    def test_convention(self):
        self.assertTrue(H5PIV.Layout.filename.exists())
        self.assertEqual(H5PIV.Layout.filename.stem, 'H5PIV')
        with H5PIV() as h5:
            self.assertIsInstance(h5.standard_name_table, StandardizedNameTable)
            self.assertEqual(h5.standard_name_table.version_number, 1)
            self.assertEqual(h5.standard_name_table.name, 'PIV_Standard_Name')

    def test_UncertaintyDataset(self):
        with tutorial.get_H5PIV('vortex_snapshot', mode='r') as h5:
            h5.DisplacementVector[:, :].compute_uncertainty(my_uncertainty_method, None, None)
