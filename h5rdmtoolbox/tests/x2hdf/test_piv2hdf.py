import argparse
import shutil
import unittest
from unittest import mock

import numpy as np

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.x2hdf import piv
from h5rdmtoolbox.x2hdf.piv import pivview2hdf


class TestPIV2HDF(unittest.TestCase):

    @mock.patch('argparse.ArgumentParser.parse_args',
                return_value=argparse.Namespace(help=True, write_default_config=None, source=None))
    def test_command(self, mock_args):
        pivview2hdf()

    def test_config(self):
        ymlfile = piv._config.write_config(h5tbx.generate_temporary_filename(suffix='.yml'),
                                           piv._config.DEFAULT_CONFIGURATION)
        self.assertTrue(piv._config.check_yaml_file(ymlfile))

    def test_parameter(self):
        pivview_parameter_file = h5tbx.tutorial.PIVview.get_parameter_file()
        par = piv.pivview.PIVviewParameterFile(pivview_parameter_file)
        par.to_dict()

        openpiv_parameter_file = h5tbx.tutorial.OpenPIV.get_parameter_file()
        par = piv.openpiv.OpenPIVParameterFile(openpiv_parameter_file)
        par.to_dict()

    def test_openpiv_snapshot(self):
        # get the test file:
        openpiv_txt_file = h5tbx.tutorial.OpenPIV.get_snapshot_txt_file()
        openpiv_par_file = h5tbx.tutorial.OpenPIV.get_parameter_file()

        # init a openpiv-file instance:
        # None -> auto serach
        openpiv_file = piv.openpiv.OpenPIVFile(openpiv_txt_file, parameter_filename=None)

        openpiv_snapshot = piv.PIVSnapshot(openpiv_file, recording_time=0.)
        hdf_filename = openpiv_snapshot.to_hdf()

    def test_pivview_snapshot(self):
        pivview_nc_file = h5tbx.tutorial.PIVview.get_snapshot_nc_files()[0]
        pivview_file = piv.PIVViewNcFile(pivview_nc_file, None)
        snapshot_pivview = piv.PIVSnapshot(pivview_file, recording_time=0.)
        hdf_filename = snapshot_pivview.to_hdf()
        with h5tbx.H5PIV(hdf_filename) as h5piv:
            self.assertEqual(h5piv.check(), 0)

    def test_multi_piv_equal_nt(self):
        plane_dirs = h5tbx.tutorial.PIVview.get_multiplane_directories()[0:2]
        plane_objs = [piv.PIVPlane.from_plane_folder(d, 5, piv.PIVViewNcFile) for d in
                      plane_dirs]
        mplane = piv.PIVMultiPlane(plane_objs)
        hdf_filename = mplane.to_hdf()
        with h5tbx.H5PIV(hdf_filename) as h5piv:
            self.assertEqual(h5piv.check(), 0)

    def test_multi_piv_unequal_nt(self):
        plane_dirs = h5tbx.tutorial.PIVview.get_multiplane_directories()
        plane_objs = [piv.PIVPlane.from_plane_folder(d, 5, piv.PIVViewNcFile) for d in
                      plane_dirs]
        mplane = piv.PIVMultiPlane(plane_objs)
        hdf_filename = mplane.to_hdf()
        with h5tbx.H5PIV(hdf_filename) as h5piv:
            self.assertEqual(h5piv.check(), 0)

    def test_multi_piv_unequal_nt2(self):
        """check what happens if first plane has more times than second and vice versa"""

        def _set_z_in_nc(nc_filename, z_val):
            with ncDataset(nc_filename, 'r+') as nc:
                nc.setncattr('origin_offset_z', z_val)
                for k, v in nc.variables.items():
                    if 'coord_min' in nc[k].ncattrs():
                        coord_min = nc[k].getncattr('coord_min')
                        coord_min[-1] = z_val
                        nc[k].setncattr('coord_min', coord_min)
                        coord_max = nc[k].getncattr('coord_max')
                        coord_max[-1] = z_val
                        nc[k].setncattr('coord_max', coord_max)

        try:
            from netCDF4 import Dataset as ncDataset
        except ImportError:
            raise ImportError('Package netCDF4 is not installed. Either install it '
                              'separately or install the repository with pip install h5RDMtolbox [piv]')
        for _switch in (True, False):
            case_dir = h5tbx.tutorial.PIVview.get_plane_directory()
            nc_files = list(case_dir.glob('*.nc'))
            casedir = h5tbx.generate_temporary_directory('case')
            plane0dir = casedir / 'plane0'
            plane1dir = casedir / 'plane1'
            plane0dir.mkdir()
            plane1dir.mkdir()
            if _switch:
                dest = shutil.copy2(nc_files[0], plane0dir)
                _set_z_in_nc(dest, -5.)
                dest = shutil.copy2(nc_files[1], plane0dir)
                _set_z_in_nc(dest, -5.)
                dest = shutil.copy2(nc_files[2], plane0dir)
                _set_z_in_nc(dest, -5.)
                dest = shutil.copy2(nc_files[3], plane0dir)
                _set_z_in_nc(dest, -5.)
                shutil.copy2(nc_files[4], plane1dir)
                shutil.copy2(nc_files[5], plane1dir)
            else:
                dest = shutil.copy2(nc_files[0], plane0dir)
                _set_z_in_nc(dest, -5.)
                dest = shutil.copy2(nc_files[1], plane0dir)
                _set_z_in_nc(dest, -5.)
                shutil.copy2(nc_files[2], plane1dir)
                shutil.copy2(nc_files[3], plane1dir)
                shutil.copy2(nc_files[4], plane1dir)
                shutil.copy2(nc_files[5], plane1dir)

            shutil.copy2(h5tbx.tutorial.PIVview.get_parameter_file(), plane0dir)
            shutil.copy2(h5tbx.tutorial.PIVview.get_parameter_file(), plane1dir)
            plane_objs = [piv.PIVPlane.from_plane_folder(d, 5, piv.PIVViewNcFile) for d in
                          [plane0dir, plane1dir]]
            mplane = piv.PIVMultiPlane(plane_objs)
            hdf_filename = mplane.to_hdf(fill_time_vec_differences=True)
            with h5tbx.H5PIV(hdf_filename) as h5:
                self.assertEqual(h5.z[0].values[()], -5.)
                self.assertEqual(h5.z[1].values[()], 0.)
                if _switch:
                    self.assertFalse(h5.u[0, 0, 0, 0].isnull())
                    self.assertFalse(h5.u[0, 1, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 0, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 1, 0, 0].isnull())
                    self.assertTrue(h5.u[1, 2, 0, 0].isnull())
                    self.assertTrue(h5.u[1, 3, 0, 0].isnull())
                    self.assertFalse(h5.u[0, 2, 0, 0].isnull())
                    self.assertFalse(h5.u[0, 3, 0, 0].isnull())
                else:
                    self.assertFalse(h5.u[0, 0, 0, 0].isnull())
                    self.assertFalse(h5.u[0, 1, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 0, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 1, 0, 0].isnull())
                    self.assertTrue(h5.u[0, 2, 0, 0].isnull())
                    self.assertTrue(h5.u[0, 3, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 2, 0, 0].isnull())
                    self.assertFalse(h5.u[1, 3, 0, 0].isnull())

    def test_multi_piv_unequal_nt_force(self):
        plane_dirs = h5tbx.tutorial.PIVview.get_multiplane_directories()
        plane_objs = [piv.PIVPlane.from_plane_folder(d, 5, piv.PIVViewNcFile) for d in
                      plane_dirs]
        mplane = piv.PIVMultiPlane(plane_objs)
        hdf_filename = mplane.to_hdf(fill_time_vec_differences=True)
        with h5tbx.H5PIV(hdf_filename, 'r') as h5piv:
            self.assertEqual(np.isnan(h5piv.u[-1, -1, :, :].values).sum(), h5piv['x'].size * h5piv['y'].size)
            self.assertEqual(h5piv.check(), 0)
            h5piv.get_parameters(0)

    def test_utils(self):
        from h5rdmtoolbox.x2hdf.piv import utils
        from pint_xarray import unit_registry
        self.assertTrue(utils.is_time('s'))
        self.assertTrue(utils.is_time(unit_registry.Unit('s')))
        self.assertTrue(utils.is_time(unit_registry.Unit('ms')))
        self.assertFalse(utils.is_time(unit_registry.Unit('m')))

        self.assertTrue(utils.is_length('m'))
        self.assertTrue(utils.is_length(unit_registry.Unit('m')))
        self.assertTrue(utils.is_length(unit_registry.Unit('km')))
        self.assertFalse(utils.is_length(unit_registry.Unit('s')))
