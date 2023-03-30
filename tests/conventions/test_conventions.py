import logging
import unittest
from pint.errors import UndefinedUnitError

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions import standard_name
from h5rdmtoolbox.wrapper.cflike import File


class TestConventions(unittest.TestCase):

    def test_logger(self):
        h5tbx.conventions.set_loglevel(logging.DEBUG)
        self.assertEqual(h5tbx.conventions.logger.level, logging.DEBUG)
        h5tbx.conventions.set_loglevel(logging.CRITICAL)
        self.assertEqual(h5tbx.conventions.logger.level, logging.CRITICAL)

    def test_pivview(self):
        with File(mode='w', standard_name_table='Test-v1') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
            self.assertFalse('standard_name' in ds.attrs)
            standard_name.StandardNameTableTranslation.print_registered()
            translation = standard_name.StandardNameTableTranslation.load_registered('test-to-Test-v1')
            translation.translate_dataset(ds)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

        with File(mode='w', standard_name_table='Test-v1') as h5:
            ds = h5.create_dataset('u', shape=(), long_name='x_velocity', units='m/s')
            self.assertFalse('standard_name' in ds.attrs)
            translation = standard_name.StandardNameTableTranslation.load_registered('test-to-Test-v1')
            translation.translate_group(h5)
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_standard_name(self):
        standard_name.StandardNameTable(name='Space In Name',
                                        table=None,
                                        version_number=999,
                                        contact='a.b@dummy.com',
                                        institution='dummyexample')
        with self.assertRaises(standard_name.EmailError):
            standard_name.StandardNameTable(name='NoSpaceInName',
                                            table=None,
                                            version_number=999,
                                            contact='wrongemail',
                                            institution='dummyexample')
        with self.assertRaises(TypeError):
            standard_name.StandardNameTable(name='NoSpaceInName',
                                            table={'a': 'amplitude'},
                                            version_number=999,
                                            contact='a.b@dummy.com',
                                            institution='dummyexample')
        snc = standard_name.StandardNameTable(name='NoSpaceInName',
                                              table={'x_velocity': {'description': 'x velocity',
                                                                    'canonical_units': 'm/s'}},
                                              version_number=999,
                                              contact='a.b@dummy.com',
                                              institution='dummyexample')
        self.assertTrue('x_velocity' in snc)
        self.assertEqual(snc.contact, 'a.b@dummy.com')
        self.assertEqual(snc.names, ['x_velocity', ])
        # self.assertTrue(snc.is_valid('x_velocity'))

        with self.assertRaises(KeyError):
            # table dict is missing entry "description"
            _ = standard_name.StandardNameTable(name='NoSpaceInName',
                                                table={'x_velocity': {'canonical_units': 'm/s'}},
                                                version_number=999,
                                                contact='a.b@dummy.com',
                                                institution='dummyexample')

        pivsnt = standard_name.StandardNameTable.load_registered('piv-v1')
        empty = standard_name.Empty_Standard_Name_Table
        with File() as h5:
            h5.standard_name_table = standard_name.Empty_Standard_Name_Table

        with File(h5.hdf_filename, standard_name_table=empty, mode='r+') as h5:
            self.assertTrue(h5.standard_name_table, empty)

        with File(standard_name_table=pivsnt) as h5:
            self.assertEqual(h5.standard_name_table, pivsnt)

        self.assertEqual(pivsnt.name, str(pivsnt))
        with self.assertRaises(standard_name.StandardNameError):
            self.assertTrue(pivsnt.check_name('hallo', strict=True))
        with self.assertRaises(standard_name.StandardNameError):
            pivsnt.check_name(' 213 ')

    def test_identifier(self):
        self.assertEqual(standard_name.verify_unit_object('s'), None)
        with self.assertRaises(UndefinedUnitError):
            self.assertFalse(standard_name.verify_unit_object('noppe'))
