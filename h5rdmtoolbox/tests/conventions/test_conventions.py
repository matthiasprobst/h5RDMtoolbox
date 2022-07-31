import unittest

from h5rdmtoolbox.conventions import translations
from h5rdmtoolbox.conventions.identifier import StandardizedNameTable, EmailError
from h5rdmtoolbox.h5wrapper import H5PIV


class TestCnventions(unittest.TestCase):

    def test_pivview(self):
        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='')
            self.assertFalse('standard_name' in ds.attrs)
            translations.update(ds)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='')
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
