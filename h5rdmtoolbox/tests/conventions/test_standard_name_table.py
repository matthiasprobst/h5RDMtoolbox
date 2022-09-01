import unittest

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions.identifier import StandardizedNameTable


class TestStandardNameTable(unittest.TestCase):

    def test_from_yml(self):
        table = StandardizedNameTable.from_yml(testdir / 'sntable.yml')
        table.sdump()
        self.assertEqual(table.translate('images', 'pivsig'), 'synthetic_particle_image')

        yaml_filename = table.to_yaml(generate_temporary_filename(suffix='.yml'))
        table2 = StandardizedNameTable.from_yml(yaml_filename)
        self.assertEqual(table, table2)
        table2.set('other', 'desc', 'm')
        self.assertNotEqual(table, table2)
