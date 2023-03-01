import unittest

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions import utils
from h5rdmtoolbox.conventions.cflike.standard_name import xmlsnt2dict, StandardNameTable


class TestTranslation(unittest.TestCase):

    def test_xml(self):
        piv_snt = StandardNameTable.load_registered('piv-v1')
        xml_filename = utils.dict2xml(generate_temporary_filename(suffix='.xml'),
                                      name=piv_snt.name,
                                      dictionary=piv_snt.table,
                                      versionname=piv_snt.versionname)
        data, meta = xmlsnt2dict(xml_filename=xml_filename)
        self.assertEqual(meta['name'], piv_snt.name, )
        self.assertEqual(meta['versionname'], piv_snt.versionname)

        html_filename = utils.xml_to_html_table_view(xml_filename=xml_filename,
                                                     html_filename=generate_temporary_filename(suffix='.html'))
        self.assertTrue(html_filename.exists())
        self.assertTrue(html_filename.stat().st_size > 0)
