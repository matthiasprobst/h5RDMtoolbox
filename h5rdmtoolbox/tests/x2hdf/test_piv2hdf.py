# import unittest
#
# import h5py
# import numpy as np
# import xarray as xr
#
# from h5rdmtoolbox import tutorial
# from h5rdmtoolbox.conventions.data import DataSourceType, DataSource
# from h5rdmtoolbox.conventions.translations import pivview_to_standardnames_dict
# from h5rdmtoolbox.utils import generate_temporary_filename
# from h5rdmtoolbox.x2hdf.piv.pivview_old import PIVMultiPlane
# from h5rdmtoolbox.x2hdf.piv.pivview_old import PIVSnapshot
# from h5rdmtoolbox.x2hdf.piv.pivview_old import plane
# from h5rdmtoolbox.x2hdf.piv.pivview_old.core import InvalidZSourceError, PIV_FILE_TYPE_NAME
# from h5rdmtoolbox.x2hdf.piv.pivview_old.snapshot import NotAFileError
#
#
# class TestPIV2HDF(unittest.TestCase):
#
#     def setUp(self) -> None:
#         self.file_ls = []
#
#     def tearDown(self) -> None:
#         for f in self.file_ls:
#             f.unlink()
#
#     def check_snapshot_content_individual_plane_data(self, snapshot_hdf_filename, iz, it, nc_filename, nz):
#         nc_ds = xr.open_dataset(nc_filename)  # read nc data with xarray
#         self.assertTrue(snapshot_hdf_filename.is_file())
#         with h5py.File(snapshot_hdf_filename, 'r') as h5:
#             self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
#             self.assertTrue('creation_time' in h5.attrs)
#             self.assertEqual(h5.attrs['piv_data_type'], PIV_FILE_TYPE_NAME['PIVMultiPlane'])
#             self.assertIn('title', h5.attrs)
#
#             plane_grp = h5[plane._generate_plane_group(iz, nz)]
#
#             mask = np.isnan(plane_grp['u'][it, :, :])
#
#             self.assertIn('x', plane_grp)
#             self.assertIn('y', plane_grp)
#             self.assertIn('ix', plane_grp)
#             self.assertIn('iy', plane_grp)
#             self.assertIn('z', plane_grp)
#             self.assertIn('time', plane_grp)
#             self.assertTrue(len(plane_grp['u'].dims[1]) == 2)
#             self.assertTrue(len(plane_grp['u'].dims[2]) == 2)
#             self.assertTrue(plane_grp['u'].dims[1][0] == plane_grp['y'])
#             self.assertTrue(plane_grp['u'].dims[1][1] == plane_grp['iy'])
#             self.assertTrue(plane_grp['u'].dims[2][0] == plane_grp['x'])
#             self.assertTrue(plane_grp['u'].dims[2][1] == plane_grp['ix'])
#
#             self.assertNotIn('x', h5)
#             self.assertNotIn('y', h5)
#             self.assertNotIn('ix', h5)
#             self.assertNotIn('iy', h5)
#             self.assertNotIn('z', h5)
#             self.assertNotIn('time', h5)
#
#             self.assertEqual(plane_grp['z'].ndim, 0)
#             self.assertEqual(plane_grp['x'].ndim, 1)
#             self.assertEqual(plane_grp['y'].ndim, 1)
#             self.assertEqual(plane_grp['ix'].ndim, 1)
#             self.assertEqual(plane_grp['iy'].ndim, 1)
#             self.assertEqual(plane_grp['time'].ndim, 1)
#
#             for i, name in enumerate(('u', 'v', 'w')):
#                 if name == 'w':
#                     if nc_ds.velocity.shape[-1] == 2:
#                         continue
#                 try:
#                     np.testing.assert_equal(plane_grp[name][it, :, :][~mask], nc_ds.velocity.values[0, ~mask, i])
#                 except Exception as e:
#                     print(f'{name}-velocity array check error @ iz={iz}, it={it}: {e}')
#                 try:
#                     self.assertEqual(plane_grp[name].attrs['units'], nc_ds.velocity.attrs['units'])
#                 except Exception as e:
#                     print(f'{name}-velocity units check error @ iz={iz}, it={it}: {e}')
#
#             np.testing.assert_equal(plane_grp['dx'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 0])
#             np.testing.assert_equal(plane_grp['dy'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 1])
#             if nc_ds.piv_data.shape[-1] == 3:
#                 np.testing.assert_equal(plane_grp['dz'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 2])
#                 self.assertEqual(plane_grp['dy'].attrs['units'], 'pixel')
#             self.assertEqual(plane_grp['dx'].attrs['units'], 'pixel')
#             self.assertEqual(plane_grp['dy'].attrs['units'], 'pixel')
#
#             # check standard names
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     try:
#                         self.assertEqual(h5[k].attrs['standard_name'], pivview_to_standardnames_dict[k])
#                     except Exception as e:
#                         print(f'Standard name missing in {k}: "{e}"')
#
#             # check dimension scales:
#             nx = plane_grp['x'].size
#             ny = plane_grp['y'].size
#             nt = plane_grp['time'].size
#             for k, v in plane_grp.items():
#                 if k not in ('x', 'y', 'time', 'z', 'ix', 'iy'):
#                     if isinstance(v, h5py.Dataset):
#                         self.assertEqual(plane_grp[k].shape, (nt, ny, nx))
#
#     def check_pure_snapshot_content(self, snapshot, nc_filename):
#         nc_ds = xr.open_dataset(nc_filename)  # read nc data with xarray
#         self.assertTrue(snapshot.hdf_filename.is_file())
#
#         with h5py.File(snapshot.hdf_filename) as h5:
#             self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
#             self.assertTrue('creation_time' in h5.attrs)
#             self.assertEqual(h5.attrs[DataSourceType.get_attr_name()], DataSourceType.experimental.name)
#             self.assertEqual(h5.attrs['title'],
#                              'PIV snapshot file generated from a single PIVview netCDF4 file.')
#
#             mask = np.isnan(h5['u'][:])
#             np.testing.assert_equal(h5['u'][~mask], nc_ds.velocity.values[0, ~mask, 0])
#             np.testing.assert_equal(h5['v'][~mask], nc_ds.velocity.values[0, ~mask, 1])
#             if nc_ds.velocity.shape[-1] == 3:
#                 np.testing.assert_equal(h5['w'][~mask], nc_ds.velocity.values[0, ~mask, 2])
#                 self.assertEqual(h5['w'].attrs['units'], nc_ds.velocity.attrs['units'])
#             self.assertEqual(h5['u'].attrs['units'], nc_ds.velocity.attrs['units'])
#             self.assertEqual(h5['v'].attrs['units'], nc_ds.velocity.attrs['units'])
#
#             np.testing.assert_equal(h5['dx'][~mask], nc_ds.piv_data.values[0, ~mask, 0])
#             np.testing.assert_equal(h5['dy'][~mask], nc_ds.piv_data.values[0, ~mask, 1])
#             if nc_ds.piv_data.shape[-1] == 3:
#                 np.testing.assert_equal(h5['dz'][~mask], nc_ds.piv_data.values[0, ~mask, 2])
#                 self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dx'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#
#             self.assertIn('x', h5)
#             self.assertIn('y', h5)
#             self.assertIn('ix', h5)
#             self.assertIn('iy', h5)
#             self.assertTrue(len(h5['u'].dims[0]) == 2)
#             self.assertTrue(h5['u'].dims[0][0] == h5['y'])
#             self.assertTrue(h5['u'].dims[0][1] == h5['iy'])
#             self.assertTrue(h5['u'].dims[1][0] == h5['x'])
#             self.assertTrue(h5['u'].dims[1][1] == h5['ix'])
#             # check standard names
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     self.assertEqual(h5[k].attrs['standard_name'], pivview_to_standardnames_dict[k])
#
#             # check for dimension scales:
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     if k not in ('x', 'y', 'z', 'time', 'ix', 'iy'):
#                         self.assertEqual(h5[k].dims[0][0], h5['y'])
#                         self.assertEqual(h5[k].dims[1][0], h5['x'])
#                         self.assertEqual(h5[k].attrs['COORDINATES'][0], 'time')
#                         self.assertEqual(h5[k].attrs['COORDINATES'][1], 'z')
#
#             nx = h5['x'].size
#             ny = h5['y'].size
#             for k in h5.keys():
#                 if k not in ('x', 'y', 'time', 'z', 'ix', 'iy'):
#                     self.assertEqual(h5[k].shape, (ny, nx))
#
#     def check_snapshot_content(self, snapshot_hdf_filename, iz, it, nc_filename):
#         nc_ds = xr.open_dataset(nc_filename)  # read nc data with xarray
#         self.assertTrue(snapshot_hdf_filename.is_file())
#         with h5py.File(snapshot_hdf_filename, 'r') as h5:
#             self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
#             self.assertTrue('creation_time' in h5.attrs)
#             self.assertEqual(h5.attrs['piv_data_type'], PIV_FILE_TYPE_NAME['PIVMultiPlane'])
#
#             self.assertIn('title', h5.attrs)
#
#             mask = np.isnan(h5['u'][iz, it, :])
#
#             for i, name in enumerate(('u', 'v', 'w')):
#                 if name == 'w':
#                     if nc_ds.velocity.shape[-1] == 2:
#                         continue
#                 try:
#                     np.testing.assert_equal(h5[name][iz, it, :, :][~mask], nc_ds.velocity.values[0, ~mask, i])
#                 except Exception as e:
#                     print(f'{name}-velocity array check error @ iz={iz}, it={it}: {e}')
#                 try:
#                     self.assertEqual(h5[name].attrs['units'], nc_ds.velocity.attrs['units'])
#                 except Exception as e:
#                     print(f'{name}-velocity units check error @ iz={iz}, it={it}: {e}')
#
#             np.testing.assert_equal(h5['dx'][iz, it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 0])
#             np.testing.assert_equal(h5['dy'][iz, it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 1])
#             if nc_ds.piv_data.shape[-1] == 3:
#                 np.testing.assert_equal(h5['dz'][iz, it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 2])
#                 self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dx'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#
#             # check standard names
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     try:
#                         self.assertEqual(h5[k].attrs['standard_name'], pivview_to_standardnames_dict[k])
#                     except Exception as e:
#                         print(f"Standard name check failed on dataset {k}: {e}")
#
#             # check dimension scales:
#             nx = h5['x'].size
#             ny = h5['y'].size
#             nz = h5['z'].size
#             nt = h5['time'].size
#             for k, v in h5.items():
#                 if k not in ('x', 'y', 'time', 'z', 'ix', 'iy'):
#                     if isinstance(v, h5py.Dataset):
#                         try:
#                             self.assertEqual(h5[k].shape, (nz, nt, ny, nx))
#                         except Exception as e:
#                             print(f'Array shape check failed for dataset {k}: "{e}"')
#
#     # def setUp(self) -> None:
#     #     hdf_files = testdir.joinpath('PIV/piv_challenge1_E/').rglob('*.hdf')
#     #     for hdf_file in hdf_files:
#     #         hdf_file.unlink()
#     #     nc_files = testdir.joinpath('PIV/piv_challenge1_E/').rglob('*._deleteme.nc')
#     #     for nc_file in nc_files:
#     #         nc_file.unlink()
#
#     def test_MultiPlane_equal_freq(self):
#         folder_plane_list = tutorial.PIVview.get_multiplane_directories()
#         piv_mplane = PIVMultiPlane(folder_plane_list, time_information=[5., 5.])
#         piv_mplane.convert()
#         self.assertTrue(piv_mplane.is_2d2c)
#         for iz in range(piv_mplane.nz):
#             for it in range(piv_mplane.nt):
#                 self.check_snapshot_content(piv_mplane.hdf_filename, iz, it, piv_mplane.planes[iz]._found_nc_files[it])
#
#     def test_MultiPlane_different_freq(self):
#         folder_plane_list = tutorial.PIVview.get_multiplane_directories()
#         piv_mplane = PIVMultiPlane(folder_plane_list, time_information=[5., 6.])
#         piv_mplane.convert()
#         self.assertTrue(piv_mplane.is_2d2c)
#         for iz in range(piv_mplane.nz):
#             for it in range(piv_mplane.nt):
#                 self.check_snapshot_content_individual_plane_data(piv_mplane.hdf_filename, iz, it,
#                                                                   piv_mplane.planes[iz]._found_nc_files[it],
#                                                                   2)
#
#     def test_MultiPlane_single_folder(self):
#         folder_plane_list = [tutorial.PIVview.get_multiplane_directories()[0], ]
#         piv_mplane = PIVMultiPlane(folder_plane_list, time_information=[5., ])
#         piv_mplane.convert()
#         self.assertTrue(piv_mplane.is_2d2c)
#         for iz in range(piv_mplane.nz):
#             for it in range(piv_mplane.nt):
#                 self.check_snapshot_content(piv_mplane.hdf_filename, iz, it,
#                                             piv_mplane.planes[iz]._found_nc_files[it])
#
#     def test_plane_interpolation(self):
#         folder_plane_list = tutorial.PIVview.get_multiplane_directories()
#         piv_mplane = PIVMultiPlane(folder_plane_list, time_information=[5., 5.])
#         self.file_ls.append(piv_mplane.convert())
#         with h5py.File(piv_mplane.hdf_filename, 'r+') as h5:
#             h5['z'][:] = [0, 1]
#         ip_hdf = piv_mplane.compute_intermediate_plane(4, only_time_averages=True)
#         ifname = piv_mplane.build_virtual_mplane_file(ip_hdf)
#         self.file_ls.append(ifname)
#
#     def test_MultiPlaneFromHDF(self):
#         """merging multiple plane HDF files into a single HDF Case file"""
#         folder_plane_list = tutorial.PIVview.get_multiplane_directories()[0:2]
#         plane_hdf_files = [plane.plane.PIVPlane(_plane, 5.).convert() for _plane in folder_plane_list]
#         piv_plane_objects = [plane.plane.PIVPlane(_plane, 5.) for _plane in folder_plane_list]
#         hdf_filename = plane.merge_multiple_plane_hdf_files(plane_hdf_files, remove_plane_hdf_files=False)
#
#         for iz in range(2):
#             for it in range(3):
#                 self.check_snapshot_content(hdf_filename, iz, it, piv_plane_objects[iz]._found_nc_files[it],
#                                             )
#
#     def test_MultiPlaneFromHDF_unequal_frequenz(self):
#         folder_plane_list = tutorial.PIVview.get_multiplane_directories()
#         plane_hdf_files = [plane.PIVPlane(folder_plane_list[0], 5.).convert(),
#                            plane.PIVPlane(folder_plane_list[1], 6.).convert()]
#         piv_plane_objects = [plane.PIVPlane(folder_plane_list[0], 5.),
#                              plane.PIVPlane(folder_plane_list[1], 6.)]
#         hdf_filename = plane.merge_multiple_plane_hdf_files(plane_hdf_files, remove_plane_hdf_files=False)
#
#         for iz in range(2):
#             for it in range(3):
#                 self.check_snapshot_content_individual_plane_data(hdf_filename, iz, it,
#                                                                   piv_plane_objects[iz]._found_nc_files[it],
#                                                                   2)
#
#     # def test_MultiPlaneFromHDF_unequalTimesteps(self):
#     #     # now, if one hdf file has more timesteps than the other, the user must decide what to do
#     #     # this is controlled via the user yaml file
#     #     folder_name = tutorial.PIVview.get_multiplane_directories()[0]
#     #     list_of_nc_files = sorted(folder_name.glob('*[0-9].nc'))
#     #     last_file_name = list_of_nc_files[-1].__str__()
#     #     shutil.copy(list_of_nc_files[-1], last_file_name.replace('.nc', '_deleteme10.nc'))
#     #     self.files_to_be_deleted.append(last_file_name.replace('.nc', '_deleteme10.nc'))
#     #
#     #     folder_plane_list = tutorial.PIVview.get_multiplane_directories()
#     #     plane_hdf_files = [plane.PIVPlane(_plane, 5.).convert() for _plane in folder_plane_list]
#     #     for plane_hdf_file in plane_hdf_files:
#     #         with h5py.File(plane_hdf_file) as h5:
#     #             self.assertIn('u', h5)
#     #     hdf_filename = plane.merge_multiple_plane_hdf_files(plane_hdf_files, take_min_nt=False)
#     #     with h5py.File(hdf_filename) as h5:
#     #         self.assertIn('u', h5['plane0'])
#
#     def test_PIVSnapshot_VTKexport(self):
#         snapshot_filename = tutorial.PIVview.get_snapshot_nc_files()[0]
#         piv_snapshot = PIVSnapshot(snapshot_filename, recording_time=0)
#         piv_snapshot.convert()
#         vtk_filename = piv_snapshot.to_vtk(vtk_filename_wo_ext=generate_temporary_filename('.vtk'))
#         self.file_ls.append(vtk_filename)
#         self.assertTrue(vtk_filename.exists())
#
#     def test_PIVCase_VTKexport(self):
#         p0, p1, p2 = tutorial.PIVview.get_multiplane_directories()
#         mpiv = PIVMultiPlane([p0, p1, p2], 5)
#         filename = mpiv.convert()
#         self.file_ls.append(filename)
#         with h5py.File(mpiv.hdf_filename) as h5:
#             np.testing.assert_equal(h5['z'][()], np.array([-5., 0., 10.]))
#         filename = mpiv.to_vtk()
#         self.file_ls.append(filename)
#
#     # def check_snapshot_content(self, snapshot, nc_filename):
#     #     nc_ds = xr.open_dataset(nc_filename)  # read nc data with xarray
#     #     self.assertTrue(snapshot.hdf_filename.is_file())
#     #
#     #     with h5py.File(snapshot.hdf_filename) as h5:
#     #         self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
#     #         self.assertTrue('creation_time' in h5.attrs)
#     #         self.assertEqual(h5.attrs[DataSourceType.get_attr_name()], DataSourceType.experimental.name)
#     #         self.assertEqual(h5.attrs['title'],
#     #                          'PIV snapshot file generated from a single PIVview netCDF4 file.')
#     #
#     #         mask = np.isnan(h5['u'][:])
#     #         np.testing.assert_equal(h5['u'][~mask], nc_ds.velocity.values[0, ~mask, 0])
#     #         np.testing.assert_equal(h5['v'][~mask], nc_ds.velocity.values[0, ~mask, 1])
#     #         if nc_ds.velocity.shape[-1] == 3:
#     #             np.testing.assert_equal(h5['w'][~mask], nc_ds.velocity.values[0, ~mask, 2])
#     #             self.assertEqual(h5['w'].attrs['units'], nc_ds.velocity.attrs['units'])
#     #         self.assertEqual(h5['u'].attrs['units'], nc_ds.velocity.attrs['units'])
#     #         self.assertEqual(h5['v'].attrs['units'], nc_ds.velocity.attrs['units'])
#     #
#     #         np.testing.assert_equal(h5['dx'][~mask], nc_ds.piv_data.values[0, ~mask, 0])
#     #         np.testing.assert_equal(h5['dy'][~mask], nc_ds.piv_data.values[0, ~mask, 1])
#     #         if nc_ds.piv_data.shape[-1] == 3:
#     #             np.testing.assert_equal(h5['dz'][~mask], nc_ds.piv_data.values[0, ~mask, 2])
#     #             self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#     #         self.assertEqual(h5['dx'].attrs['units'], 'pixel')
#     #         self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#     #
#     #         self.assertIn('x', h5)
#     #         self.assertIn('y', h5)
#     #         self.assertIn('ix', h5)
#     #         self.assertIn('iy', h5)
#     #         self.assertTrue(len(h5['u'].dims[0]) == 2)
#     #         self.assertTrue(h5['u'].dims[0][0] == h5['y'])
#     #         self.assertTrue(h5['u'].dims[0][1] == h5['iy'])
#     #         self.assertTrue(h5['u'].dims[1][0] == h5['x'])
#     #         self.assertTrue(h5['u'].dims[1][1] == h5['ix'])
#     #         # check standard names
#     #         for k in h5.keys():
#     #             if isinstance(h5[k], h5py.Dataset):
#     #                 self.assertEqual(h5[k].attrs['standard_name'], pivview_to_standardnames_dict[k])
#     #
#     #         # check for dimension scales:
#     #         for k in h5.keys():
#     #             if isinstance(h5[k], h5py.Dataset):
#     #                 if k not in ('x', 'y', 'z', 'time', 'ix', 'iy'):
#     #                     self.assertEqual(h5[k].dims[0][0], h5['y'])
#     #                     self.assertEqual(h5[k].dims[1][0], h5['x'])
#     #                     self.assertEqual(h5[k].attrs['COORDINATES'][0], 'time')
#     #                     self.assertEqual(h5[k].attrs['COORDINATES'][1], 'z')
#     #
#     #         nx = h5['x'].size
#     #         ny = h5['y'].size
#     #         for k in h5.keys():
#     #             if k not in ('x', 'y', 'time', 'z', 'ix', 'iy'):
#     #                 self.assertEqual(h5[k].shape, (ny, nx))
#
#     def test_wrong_init(self):
#         # passing a folder instead of a file must raise an error:
#         nc_filename = tutorial.PIVview.get_snapshot_nc_files()[0]
#         with self.assertRaises(NotAFileError):
#             _ = PIVSnapshot(nc_filename.parent, recording_time=0)
#
#     def test_2D2C(self):
#         nc_filename = tutorial.PIVview.get_snapshot_nc_files()[0]
#         snapshot = PIVSnapshot(nc_filename, recording_time=0, ignore_parameter_file=True)
#
#         # try a wrong z-source value
#         with self.assertRaises(InvalidZSourceError):
#             snapshot.convert(configuration={'z_source': 'n.a.'})
#
#         # now this should work
#         snapshot.convert(configuration={'interpolation': True, 'z_source': 'coord_min'})
#
#         self.check_pure_snapshot_content(snapshot, nc_filename)
#         self.file_ls.append(snapshot.hdf_filename)
#
#     def test_from_dat(self):
#         name_avg = tutorial.PIVview.get_avg_file()
#         name_rms = tutorial.PIVview.get_rms_file()
#         name_reyn = tutorial.PIVview.get_reyn_file()
#         hdf_file = plane.build_plane_hdf_from_average_dat_files(
#             avg_dat_file=name_avg,
#             reyn_dat_file=name_reyn,
#             rms_dat_file=name_rms,
#             target=generate_temporary_filename(suffix='.hdf'))
#         with h5py.File(hdf_file, 'r') as h5:
#             self.assertEqual(h5['x'].ndim, 1)
#             self.assertEqual(h5['y'].ndim, 1)
#             self.assertEqual(h5['z'].ndim, 0)
#
#     def check_snapshot_content_of_pure_plane(self, snapshot, it, nc_filename):
#         nc_ds = xr.open_dataset(nc_filename)  # read nc data with xarray
#         self.assertTrue(snapshot.hdf_filename.is_file())
#         with h5py.File(snapshot.hdf_filename, 'r') as h5:
#             self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
#             self.assertTrue('creation_time' in h5.attrs)
#             self.assertEqual(h5.attrs[DataSourceType.get_attr_name()], DataSourceType.experimental.name)
#             self.assertEqual(h5.attrs[DataSource.get_attr_name()], DataSource.particle_image_velocimetry.name)
#             self.assertIn('title', h5.attrs)
#
#             mask = np.isnan(h5['u'][it, :])
#             np.testing.assert_equal(h5['u'][it, :, :][~mask], nc_ds.velocity.values[0, ~mask, 0])
#             np.testing.assert_equal(h5['v'][it, :, :][~mask], nc_ds.velocity.values[0, ~mask, 1])
#             if nc_ds.velocity.shape[-1] == 3:
#                 np.testing.assert_equal(h5['w'][it, :, :][~mask], nc_ds.velocity.values[0, ~mask, 2])
#                 self.assertEqual(h5['w'].attrs['units'], nc_ds.velocity.attrs['units'])
#             self.assertEqual(h5['u'].attrs['units'], nc_ds.velocity.attrs['units'])
#             self.assertEqual(h5['v'].attrs['units'], nc_ds.velocity.attrs['units'])
#
#             np.testing.assert_equal(h5['dx'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 0])
#             np.testing.assert_equal(h5['dy'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 1])
#             if nc_ds.piv_data.shape[-1] == 3:
#                 np.testing.assert_equal(h5['dz'][it, :, :][~mask], nc_ds.piv_data.values[0, ~mask, 2])
#                 self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dx'].attrs['units'], 'pixel')
#             self.assertEqual(h5['dy'].attrs['units'], 'pixel')
#
#             # check for dimension scales:
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     if k not in ('ix', 'iy', 'x', 'y', 'z', 'time'):
#                         self.assertEqual(h5[k].dims[0][0], h5['time'])
#                         self.assertEqual(h5[k].dims[1][0], h5['y'])
#                         self.assertEqual(h5[k].dims[2][0], h5['x'])
#                         self.assertEqual(h5[k].attrs['COORDINATES'][0], 'z')
#
#             # check standard names
#             for k in h5.keys():
#                 if isinstance(h5[k], h5py.Dataset):
#                     self.assertEqual(h5[k].attrs['standard_name'], pivview_to_standardnames_dict[k])
#
#             self.assertIn('x', h5)
#             self.assertIn('y', h5)
#             self.assertIn('ix', h5)
#             self.assertIn('iy', h5)
#             self.assertTrue(len(h5['u'].dims[1]) == 2)
#             self.assertTrue(len(h5['u'].dims[2]) == 2)
#             self.assertTrue(h5['u'].dims[1][0] == h5['y'])
#             self.assertTrue(h5['u'].dims[1][1] == h5['iy'])
#             self.assertTrue(h5['u'].dims[2][0] == h5['x'])
#             self.assertTrue(h5['u'].dims[2][1] == h5['ix'])
#
#             # check dimension scales:
#             nx = h5['x'].size
#             ny = h5['y'].size
#             nt = h5['time'].size
#             for k, v in h5.items():
#                 if k not in ('x', 'y', 'time', 'z', 'ix', 'iy'):
#                     if isinstance(v, h5py.Dataset):
#                         self.assertEqual(h5[k].shape, (nt, ny, nx))
#
#     def test_PIVPlane2_2D2C(self):
#         name = tutorial.PIVview.get_multiplane_directories()[0]
#         piv_plane = plane.PIVPlane(name, 5.)
#         piv_plane.convert()
#         self.assertEqual(len(piv_plane), 3)
#         self.assertEqual(piv_plane.shape, (3, 15, 31))
#         self.assertTrue(piv_plane.is_2d2c)
#         for it in range(piv_plane.nt):
#             self.check_snapshot_content_of_pure_plane(piv_plane, it, piv_plane._found_nc_files[it])
