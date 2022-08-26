import unittest
from pprint import pprint

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions import translations
from h5rdmtoolbox.conventions.identifier import StandardizedNameTable

class TestStandardNameTable(unittest.TestCase):

    def test_from_yml(self):
        table = StandardizedNameTable.from_yml('sntable.yml')
        table.sdump()
        self.assertEqual(table.translate('images', 'synthetic_particle_image'))
