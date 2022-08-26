import unittest

from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions.identifier import StandardizedNameTable


class TestStandardNameTable(unittest.TestCase):

    def test_from_yml(self):
        table = StandardizedNameTable.from_yml(testdir / 'sntable.yml')
        table.sdump()
        self.assertEqual(table.translate('images', 'pivsig'), 'synthetic_particle_image')
