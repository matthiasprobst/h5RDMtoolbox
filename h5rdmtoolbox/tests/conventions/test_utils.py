import unittest

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions import utils
from h5rdmtoolbox.conventions.standard_attributes.stdatt_standard_name import xmlconvention2dict, StandardNameTable


class TestTranslation(unittest.TestCase):

    def test_xml(self):
        PIVStandardNameTable = StandardNameTable.load_registered('piv-v1')
        xml_filename = utils.dict2xml(generate_temporary_filename(suffix='.xml'),
                                      name=PIVStandardNameTable.name,
                                      dictionary=PIVStandardNameTable._dict,
                                      versionname=PIVStandardNameTable.versionname)
        data, meta = xmlconvention2dict(xml_filename=xml_filename)
        self.assertEqual(meta['name'], PIVStandardNameTable.name, )
        self.assertEqual(meta['versionname'], PIVStandardNameTable.versionname)
