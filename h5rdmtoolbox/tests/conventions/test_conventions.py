import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions import translations, Empty_Standard_Name_Table
from h5rdmtoolbox.conventions.identifier import StandardizedNameTable, EmailError
from h5rdmtoolbox.conventions.translations import pivview_to_standardnames_dict
from h5rdmtoolbox.h5wrapper import H5PIV


class TestCnventions(unittest.TestCase):

    def test_pivview(self):
        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
            self.assertFalse('standard_name' in ds.attrs)
            translations.update(ds, pivview_to_standardnames_dict)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
            self.assertFalse('standard_name' in ds.attrs)
            translations.update_standard_names(h5)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_standard_name(self):
        StandardizedNameTable(name='Space In Name',
                              table_dict=None,
                              version_number=999,
                              contact='a.b@dummy.com',
                              institution='dummyexample')
        with self.assertRaises(EmailError):
            StandardizedNameTable(name='NoSpaceInName',
                                  table_dict=None,
                                  version_number=999,
                                  contact='wrongemail',
                                  institution='dummyexample')
        with self.assertRaises(KeyError):
            StandardizedNameTable(name='NoSpaceInName',
                                  table_dict={'a': 'amplitude'},
                                  version_number=999,
                                  contact='a.b@dummy.com',
                                  institution='dummyexample')
        snc = StandardizedNameTable(name='NoSpaceInName',
                                    table_dict={'x_velocity': {'description': 'x velocity',
                                                               'canoncical_units': 'm/s'}},
                                    version_number=999,
                                    contact='a.b@dummy.com',
                                    institution='dummyexample')
        self.assertTrue('x_velocity' in snc)
        self.assertEqual(snc.contact, 'a.b@dummy.com')
        self.assertEqual(snc.names, ['x_velocity', ])
        # self.assertTrue(snc.is_valid('x_velocity'))

        with self.assertRaises(KeyError):
            # table dict is missing entry "description"
            _ = StandardizedNameTable(name='NoSpaceInName',
                                      table_dict={'x_velocity': {'canoncical_units': 'm/s'}},
                                      version_number=999,
                                      contact='a.b@dummy.com',
                                      institution='dummyexample')

        snt = StandardizedNameTable.from_name_and_version('fluid', 1)
        self.assertIsInstance(snt, StandardizedNameTable)

        fluid = StandardizedNameTable.from_name_and_version('fluid', 1)
        empty = Empty_Standard_Name_Table
        with h5tbx.H5File() as h5:
            h5.standard_name_table = Empty_Standard_Name_Table
        with h5tbx.H5File(standard_name_table=fluid) as h5:
            pass

        with self.assertWarns(h5tbx.conventions.identifier.StandardizedNameTableWarning):
            with h5tbx.H5File(h5.hdf_filename, standard_name_table=fluid) as h5:
                pass
        with self.assertRaises(h5tbx.conventions.identifier.StandardizedNameTableError):
            with h5tbx.H5File(h5.hdf_filename, standard_name_table=empty) as h5:
                pass
