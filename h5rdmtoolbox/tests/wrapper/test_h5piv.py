import unittest

import numpy as np
import packaging
import xarray as xr

import h5rdmtoolbox as h5tbx
import h5rdmtoolbox.tutorial
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.standard_attributes.standard_name import StandardNameTable
from h5rdmtoolbox.wrapper import H5PIV
from h5rdmtoolbox.wrapper import h5piv
from h5rdmtoolbox.wrapper.h5piv import PIVParameters, PIVMethod


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

    def test_H5PIV_properties(self):
        with h5rdmtoolbox.tutorial.get_H5PIV('minimal_flow', 'r+') as h5:
            del h5['u']
            h5.create_dataset('u', shape=h5['v'].shape,
                              units='m/s', standard_name='x_velocity')

            self.assertIsInstance(h5.software, h5piv.Software)
            self.assertEqual(h5.software.name, 'PIVTec PIVview')
            self.assertEqual(h5.software.version, None)
            self.assertEqual(h5.software.url, None)
            self.assertEqual(h5.software.description, None)

            h5.software = h5piv.Software(name='PIVview',
                                         version='3.8.6',
                                         url='www.pivtec.com/pivview.html',
                                         description='PIV processing')
            self.assertIsInstance(h5.software, h5piv.Software)
            self.assertEqual(h5.software.name, 'PIVview')
            self.assertEqual(h5.software.version, packaging.version.parse('3.8.6'))
            self.assertEqual(str(h5.software.version), '3.8.6')
            self.assertEqual(h5.software.name, 'PIVview')

            with self.assertRaises(TypeError):
                h5.attrs['software'] = ('PIVview', '3.8.6',
                                        'www.pivtec.com/pivview.html',
                                        'PIV processing')

            h5.attrs['software'] = dict(name='PIVview',
                                        version='3.8.0',
                                        url='www.pivtec.com/pivview.html',
                                        description='PIV processing')
            self.assertIsInstance(h5.software, h5piv.Software)
            self.assertEqual(h5.software.name, 'PIVview')
            self.assertEqual(h5.software.version.__str__(), '3.8.0')

            h5.software = h5piv.Software(name='PIVview',
                                         version='3.8.6',
                                         url='www.pivtec.com/pivview.html',
                                         description='PIV processing')

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

    def test_vdp(self):
        with h5tbx.tutorial.get_H5PIV('vortex_snapshot', 'r+') as h5:
            if 'flag_translation' in h5['piv_flags'].attrs:
                h5['piv_flags'].attrs.rename('flag_translation', 'flag_meanings')
            h5['piv_flags'].compute_vdp()

    def test_VelocityDataset(self):
        with tutorial.get_H5PIV('vortex_snapshot', mode='r') as h5:
            h5.VelocityVector[:, :]

    def test_convention(self):
        with H5PIV() as h5:
            self.assertIsInstance(h5.standard_name_table, StandardNameTable)
            self.assertEqual(h5.standard_name_table.version_number, 1)
            self.assertEqual(h5.standard_name_table.name, 'piv')

    def test_UncertaintyDataset(self):
        with tutorial.get_H5PIV('vortex_snapshot', mode='r') as h5:
            h5.DisplacementVector[:, :].compute_uncertainty(my_uncertainty_method, None, None)

    def test_piv_parameters2(self):
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
