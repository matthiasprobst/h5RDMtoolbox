import pint
import unittest

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.standard_attributes import StandardNameTable
from h5rdmtoolbox.conventions.standard_attributes import utils
from h5rdmtoolbox.conventions.standard_attributes.utils import xmlsnt2dict, dict2xml, xml_to_html_table_view


class TestTranslation(unittest.TestCase):

    def test_equal_base_units(self):
        u1 = pint.Unit('m')
        u2 = pint.Unit('km')
        u3 = pint.Unit('m/s')
        self.assertTrue(utils.equal_base_units(u1, u1))
        self.assertTrue(utils.equal_base_units(u1, u2))
        self.assertFalse(utils.equal_base_units(u1, u3))

    def test_is_valid_email_address(self):
        self.assertTrue(utils.is_valid_email_address('hallo@gmail.com'))
        self.assertFalse(utils.is_valid_email_address('hallo@gmail'))
        self.assertFalse(utils.is_valid_email_address('hallo.de'))

    def test_check_url(self):
        with self.assertWarns(UserWarning):
            utils.check_url('www.no-google.de', raise_error=False, print_warning=True)
        with self.assertWarns(UserWarning):
            utils.check_url('https://www.no-google.de', raise_error=False, print_warning=True)
        with self.assertRaises(Exception):
            utils.check_url('https://www.no-google.de', raise_error=True, print_warning=False)
        with self.assertRaises(ValueError):
            utils.check_url('https://www.no-google.de', raise_error=True, print_warning=True)

    def test_xml(self):
        regs = StandardNameTable.get_registered()
        piv_snt = StandardNameTable.load_registered('piv-v1')
        xml_filename = dict2xml(generate_temporary_filename(suffix='.xml'),
                                name=piv_snt.name,
                                dictionary=piv_snt.standard_names,
                                versionname=piv_snt.versionname)
        data, meta = xmlsnt2dict(xml_filename=xml_filename)
        self.assertEqual(meta['name'], piv_snt.name, )
        self.assertEqual(meta['versionname'], piv_snt.versionname)

        html_filename = xml_to_html_table_view(xml_filename=xml_filename,
                                               html_filename=generate_temporary_filename(suffix='.html'))
        self.assertTrue(html_filename.exists())
        self.assertTrue(html_filename.stat().st_size > 0)
