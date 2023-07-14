import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use('tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'tbx')

    def test_standard_name_table_from_yaml(self):
        snt_yaml = tutorial.get_standard_name_table_yaml_file()
        snt = h5tbx.conventions.tbx.StandardNameTable.from_yaml(snt_yaml)
        self.assertEqual(snt.name, 'Test')
        self.assertEqual(snt.version_number, 1)
        self.assertIsInstance(snt.table, dict)
        self.assertEqual(snt.table['time'], {'units': 's',
                                             'description': 'physical time'})
        self.assertIsInstance(snt['time'], h5tbx.conventions.tbx.StandardName)

    def test_standard_name_table_from_xml(self):
        cf = h5tbx.conventions.tbx.StandardNameTable.from_web(
            url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml')
        self.assertEqual(cf.name, 'standard_name_table')

    def test_standard_name_table_to_xml(self):
        cf = h5tbx.conventions.tbx.StandardNameTable.from_web(
            url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml')
        xml_filename = h5tbx.generate_temporary_filename(suffix='.xml')
        cf.to_xml(xml_filename)
