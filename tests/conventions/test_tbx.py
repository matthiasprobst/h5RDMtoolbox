import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use('tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'tbx')

    def test_read_convention_from_yaml(self):
        from h5rdmtoolbox.conventions.standard_attribute import StandardAttribute
        from h5rdmtoolbox.conventions import Convention
        yaml_filename = r'C:\Users\da4323\Documents\programming\GitHub\h5RDMtoolbox\h5rdmtoolbox\data\tbx_convention.yaml'


        my_convention = Convention.from_yaml(yaml_filename, name='myconvention')
        my_convention.register()
        h5tbx.use('myconvention')

        with h5tbx.File(title='Hi I am a title',
                        contact='https://orcid.org/0000-0001-8729-0482') as h5:
            ds = h5.create_dataset('velocity',
                                   data=1.2,
                                   units='pixel',
                                   scale='10 m/s/pixel',
                                   long_name='a velocity')

    def test_comment(self):
        h5tbx.use('tbx')
        from h5rdmtoolbox.conventions.standard_attribute import StandardAttribute
        import yaml
        with open(r'C:/Users/da4323/Documents/programming/GitHub/h5RDMtoolbox/docs/conventions/std_attr.yaml') as f:
            std_dict = yaml.safe_load(f)

        title_attr = StandardAttribute(name='title', **std_dict['title'])
        units_attr = StandardAttribute(name='units', **std_dict['units'])
        h5tbx.conventions.current_convention.add(title_attr)
        h5tbx.conventions.current_convention.add(units_attr)
        with h5tbx.File(title='Hi I am a title') as h5:
            ds = h5.create_dataset('velocity', data=1.2, units='pixel', scale='10 m/s/pixel')
            # print(ds.scale)
            print(ds[()].units)
            h5tbx.set_config(ureg_format='')
            print(ds[()].units)
            # ds.units = 'mm/s'

    def test_standard_name_table_from_yaml(self):
        snt_yaml = tutorial.get_standard_name_table_yaml_file()
        snt = h5tbx.conventions.tbx.StandardNameTable.from_yaml(snt_yaml)
        self.assertEqual(snt.name, 'Test')
        self.assertEqual(snt.version, 'v1.0')
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
