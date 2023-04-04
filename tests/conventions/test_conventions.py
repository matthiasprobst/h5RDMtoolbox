import unittest

import h5rdmtoolbox as h5tbx


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use('h5py')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use('tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('tbx2')

#
#     def test_pivview(self):
#         with File(mode='w', standard_name_table='Test-v1') as h5:
#             ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
#             self.assertFalse('standard_name' in ds.attrs)
#             standard_name.StandardNameTableTranslation.print_registered()
#             translation = standard_name.StandardNameTableTranslation.load_registered('test-to-Test-v1')
#             translation.translate_dataset(ds)
#             self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
#
#         with File(mode='w', standard_name_table='Test-v1') as h5:
#             ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
#             self.assertFalse('standard_name' in ds.attrs)
#             translation = standard_name.StandardNameTableTranslation.load_registered('test-to-Test-v1')
#             translation.translate_group(h5)
#             self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
#
#     def test_standard_name(self):
#         standard_name.StandardNameTable(name='Space In Name',
#                                         table=None,
#                                         version_number=999,
#                                         contact='a.b@dummy.com',
#                                         institution='dummyexample')
#         with self.assertRaises(standard_name.EmailError):
#             standard_name.StandardNameTable(name='NoSpaceInName',
#                                             table=None,
#                                             version_number=999,
#                                             contact='wrongemail',
#                                             institution='dummyexample')
#         with self.assertRaises(TypeError):
#             standard_name.StandardNameTable(name='NoSpaceInName',
#                                             table={'a': 'amplitude'},
#                                             version_number=999,
#                                             contact='a.b@dummy.com',
#                                             institution='dummyexample')
#         snc = standard_name.StandardNameTable(name='NoSpaceInName',
#                                               table={'x_velocity': {'description': 'x velocity',
#                                                                     'canonical_units': 'm/s'}},
#                                               version_number=999,
#                                               contact='a.b@dummy.com',
#                                               institution='dummyexample')
#         self.assertTrue('x_velocity' in snc)
#         self.assertEqual(snc.contact, 'a.b@dummy.com')
#         self.assertEqual(snc.names, ['x_velocity', ])
#         # self.assertTrue(snc.is_valid('x_velocity'))
#
#         with self.assertRaises(KeyError):
#             # table dict is missing entry "description"
#             _ = standard_name.StandardNameTable(name='NoSpaceInName',
#                                                 table={'x_velocity': {'canonical_units': 'm/s'}},
#                                                 version_number=999,
#                                                 contact='a.b@dummy.com',
#                                                 institution='dummyexample')
#
#         pivsnt = standard_name.StandardNameTable.load_registered('piv-v1')
#         empty = standard_name.Empty_Standard_Name_Table
#         with File() as h5:
#             h5.standard_name_table = standard_name.Empty_Standard_Name_Table
#
#         with File(h5.hdf_filename, standard_name_table=empty, mode='r+') as h5:
#             self.assertTrue(h5.standard_name_table, empty)
#
#         with File(standard_name_table=pivsnt) as h5:
#             self.assertEqual(h5.standard_name_table, pivsnt)
#
#         self.assertEqual(pivsnt.name, str(pivsnt))
#         with self.assertRaises(standard_name.StandardNameError):
#             self.assertTrue(pivsnt.check_name('hallo', strict=True))
#         with self.assertRaises(standard_name.StandardNameError):
#             pivsnt.check_name(' 213 ')
#
#     def test_identifier(self):
#         self.assertEqual(standard_name.verify_unit_object('s'), None)
#         with self.assertRaises(UndefinedUnitError):
#             self.assertFalse(standard_name.verify_unit_object('noppe'))
