import unittest

from h5rdmtoolbox.conventions import pivview, standard_names
from h5rdmtoolbox.h5wrapper import H5PIV


class TestCnventions(unittest.TestCase):

    def test_pivview(self):
        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity')
            self.assertFalse('standard_name' in ds.attrs)
            pivview.update(ds)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

        with H5PIV(mode='w') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity')
            self.assertFalse('standard_name' in ds.attrs)
            pivview.update_standard_names(h5)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_standard_name(self):
        with self.assertRaises(ValueError):
            standard_names.StandardNameConvention(standard_name_dict=None,
                                                  name='Space In Name',
                                                  version=999,
                                                  contact='a.b@dummy.com',
                                                  institution='dummyexample')
        with self.assertRaises(ValueError):
            standard_names.StandardNameConvention(standard_name_dict=None,
                                                  name='NoSpaceInName',
                                                  version=999,
                                                  contact='wrongemail',
                                                  institution='dummyexample')
        with self.assertRaises(ValueError):
            standard_names.StandardNameConvention(standard_name_dict={'a': 'amplitude'},
                                                  name='NoSpaceInName',
                                                  version=999,
                                                  contact='a.b@dummy.com',
                                                  institution='dummyexample')
        snc = standard_names.StandardNameConvention(standard_name_dict={'x_velocity': {'description': 'x velocity',
                                                                                       'canoncical_units': 'm/s'}},
                                                    name='NoSpaceInName',
                                                    version=999,
                                                    contact='a.b@dummy.com',
                                                    institution='dummyexample')
        self.assertTrue('x_velocity' in snc)
        self.assertTrue(snc._verify_dict())
        self.assertEqual(snc.contact, 'a.b@dummy.com')
        self.assertEqual(snc.names, ['x_velocity', ])
        self.assertTrue(snc.is_valid('x_velocity'))
