# import unittest
#
# import h5py
#
# from h5rdmtoolbox.h5wrapper import H5Base
#
#
# class TestH5Base(unittest.TestCase):
#
#     def test_attrs(self):
#         with H5Base() as h5:
#             h5.attrs['a_attr'] = 'a_string'
#             h5.attrs['standard_name'] = 'a_string'
#
#             ds = h5.create_dataset('ds', shape=())
#             ds.attrs['a_attr'] = 'a_string'
#             ds.attrs['standard_name'] = 'CoordinateX'
#             gr = h5.create_group('gr')
#             gr.attrs['a_attr'] = 'a_string'
#
#     def test_Layout(self):
#         self.assertTrue(H5Base.Layout.filename.exists())
#         self.assertEqual(H5Base.Layout.filename.stem, 'H5Base')
#         with H5Base() as h5:
#             n_issuess = h5.check()
#             self.assertEqual(n_issuess, 0)
#             h5.title = 'my title'
#             n_issuess = h5.check()
#             self.assertEqual(n_issuess, 0)
#
#     def test_special_attribute(self):
#         with H5Base() as h5:
#             ds = h5.create_dataset('x', data=1)
#             h5.attrs['link_to_ds'] = ds
#             self.assertIsInstance(h5.attrs['link_to_ds'], h5py.Dataset)
#             ds.attrs['link_to_ds'] = ds
#             self.assertIsInstance(ds.attrs['link_to_ds'], h5py.Dataset)
#             h5.attrs['attibute_of_links_to_ds'] = {'x': ds, 'xcopy': ds, 'astr': 'test', 'afloat': 3.1}
#             self.assertIsInstance(h5.attrs['attibute_of_links_to_ds'], dict)
#             self.assertIsInstance(h5.attrs['attibute_of_links_to_ds']['x'], h5py.Dataset)
#             self.assertIsInstance(h5.attrs['attibute_of_links_to_ds']['xcopy'], h5py.Dataset)
#             self.assertEqual(h5.attrs['attibute_of_links_to_ds']['xcopy'], ds)
#             self.assertIsInstance(h5.attrs['attibute_of_links_to_ds']['astr'], str)
#             self.assertIsInstance(h5.attrs['attibute_of_links_to_ds']['afloat'], float)
#             ds.attrs['attibute_of_links_to_ds'] = {'x': ds, 'xcopy': ds, 'astr': 'test', 'afloat': 3.1}
#
#             self.assertIsInstance(ds.attrs['attibute_of_links_to_ds'], dict)
#             self.assertIsInstance(ds.attrs['attibute_of_links_to_ds']['x'], h5py.Dataset)
#             self.assertIsInstance(ds.attrs['attibute_of_links_to_ds']['xcopy'], h5py.Dataset)
#             self.assertEqual(ds.attrs['attibute_of_links_to_ds']['xcopy'], ds)
#             self.assertIsInstance(ds.attrs['attibute_of_links_to_ds']['astr'], str)
#             self.assertIsInstance(ds.attrs['attibute_of_links_to_ds']['afloat'], float)
#
#     def test_create_dataset_from_image(self):
#         # just call the tutorial
#         from h5rdmtoolbox import tutorial
#         with tutorial.get_H5PIV('vortex_snapshot', 'r+') as h5:
#             pass
