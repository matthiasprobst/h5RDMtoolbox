import unittest

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions.standard_attributes.stdatt_standard_name import StandardNameTable
from h5rdmtoolbox.conventions.standard_attributes.stdatt_standard_name import merge


class TestStandardNameTable(unittest.TestCase):

    def test_from_yml(self):
        table = StandardNameTable.from_yml(testdir / 'sntable.yml')
        table.sdump()
        self.assertEqual(table.translate('images', 'pivsig'), 'synthetic_particle_image')

        yaml_filename = table.to_yaml(generate_temporary_filename(suffix='.yml'))
        table2 = StandardNameTable.from_yml(yaml_filename)
        self.assertEqual(table, table2)
        table2.set('other', 'desc', 'm')
        self.assertNotEqual(table, table2)

    def test_merge(self):
        registered_snts = StandardNameTable.get_registered()
        new_snt = merge(registered_snts, name='newtable', institution=None,
                        version_number=1, contact='matthias.probst@kit.edu')
        self.assertTrue(new_snt.name, 'newtable')
