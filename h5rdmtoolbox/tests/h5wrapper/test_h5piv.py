import unittest

import h5py
import numpy as np
import xarray as xr

import h5rdmtoolbox.tutorial
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions import StandardizedNameTable
from h5rdmtoolbox.h5wrapper import H5PIV
from h5rdmtoolbox.h5wrapper import h5piv
from h5rdmtoolbox.h5wrapper.h5piv import PIVParameters, PIVMethod


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

    def test_Layout(self):
        filename = H5PIV.layout.write()
        self.assertTrue(filename.exists())
        with h5py.File(filename) as h5:
            for a in ('title',):
                self.assertIn(a, h5.attrs)
            for ds_name in ('x', 'y', 'z'):
                self.assertIn(ds_name, h5.keys())
                for a in ('units', 'standard_name'):
                    self.assertIn(a, h5[ds_name].attrs)

    def test_H5PIV_properties(self):
        with h5rdmtoolbox.tutorial.get_H5PIV('minimal_flow', 'r+') as h5:
            del h5['u']
            h5.create_dataset('u', shape=h5['v'].shape,
                              units='m/s', standard_name='x_velocity')

            self.assertIsInstance(h5.software, h5piv.PIVSoftware)
            self.assertEqual(h5.software.name, 'PIVTec PIVview')
            self.assertEqual(h5.software.version, None)

            h5.software = h5piv.PIVSoftware('test', 3.4,
                                            extra='test')
            self.assertIsInstance(h5.software, h5piv.PIVSoftware)
            self.assertEqual(h5.software.name, 'test')
            self.assertEqual(h5.software.version, '3.4')
            self.assertEqual(h5.software['extra'], 'test')
            self.assertEqual(h5.software['name'], 'test')
            self.assertEqual(h5.software['version'], '3.4')

            h5.attrs['software'] = ('PIVview', 3.4)
            self.assertIsInstance(h5.software, h5piv.PIVSoftware)
            self.assertEqual(h5.software.name, 'PIVview')
            self.assertEqual(h5.software.version, '3.4')

            h5.software = h5piv.PIVSoftware('PIVTec PIVview', 999)

            _min, _max = h5.extent
            self.assertTupleEqual(_min, (min(h5['x'][:]),
                                         min(h5['y'][:]),
                                         min(h5['z'][:])))
            self.assertTupleEqual(_max, (max(h5['x'][:]),
                                         max(h5['y'][:]),
                                         max(h5['z'][:])))
            self.assertEqual(h5.ntimesteps, h5['time'].size)
            self.assertEqual(h5.nplanes, h5['z'].size)
            del h5['time']
            del h5['z']
            with self.assertRaises(KeyError):
                self.assertEqual(h5.ntimesteps, h5['time'].size)
            with self.assertRaises(KeyError):
                self.assertEqual(h5.nplanes, h5['z'].size)

    def test_convention(self):
        self.assertTrue(H5PIV.layout.filename.exists())
        self.assertEqual(H5PIV.layout.filename.stem, 'H5PIV')
        with H5PIV() as h5:
            self.assertIsInstance(h5.standard_name_table, StandardizedNameTable)
            self.assertEqual(h5.standard_name_table.version_number, 1)
            self.assertEqual(h5.standard_name_table.name, 'piv')

    def test_UncertaintyDataset(self):
        with tutorial.get_H5PIV('vortex_snapshot', mode='r') as h5:
            h5.DisplacementVector[:, :].compute_uncertainty(my_uncertainty_method, None, None)

    def test_piv_parameters(self):
        with tutorial.get_H5PIV('vortex_snapshot') as h5:
            piv_param = h5.get_parameters()

        self.assertIsInstance(piv_param, PIVParameters)
        self.assertIsInstance(piv_param.method, PIVMethod)
        self.assertIsInstance(piv_param.final_window_size, list)
        self.assertIsInstance(piv_param.correlation_mode, h5piv.PIVCorrelationMode)
        self.assertIsInstance(piv_param.window_function, h5piv.PIVWindowFunction)
        self.assertIsInstance(piv_param.window_function, h5piv.PIVWindowFunction)
        self.assertEqual(piv_param.window_function, h5piv.PIVWindowFunction.Gauss)
        # TODO:
        # self.assertIsInstance(piv_param.final_effective_window_size, PIVMethod)  # compute from final window size
