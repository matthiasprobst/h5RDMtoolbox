import pathlib
import unittest

import h5rdmtoolbox as h5tbx
import ontolutils
from h5rdmtoolbox import __version__
from h5rdmtoolbox.wrapper import jsonld

logger = h5tbx.logger
# logger.setLevel('ERROR')
__this_dir__ = pathlib.Path(__file__).parent


class TestCore(unittest.TestCase):

    def test_dump_hdf_to_json(self):
        """similar yet different to https://hdf5-json.readthedocs.io/en/latest/index.html"""
        import h5py
        with h5py.File('test.hdf', 'w') as h5:
            h5.attrs['version'] = __version__

        # def dump_hdf_to_json(h5_filename):
        with h5py.File('test.hdf', 'r') as h5:
            print(jsonld.dumps(h5))

    def test_to_hdf(self):
        test_data = """{"@context": {"foaf": "http://xmlns.com/foaf/0.1/", "prov": "http://www.w3.org/ns/prov#",
"schema": "http://www.w3.org/2000/01/rdf-schema#",
 "schema": "https://schema.org/",
 "local": "http://example.org/"},
"@id": "local:testperson",
"@type": "prov:Person",
"foaf:firstName": "John",
"foaf:lastName": "Doe",
"age": 1,
"schema:affiliation": {
    "@id": "local:affiliation",
    "@type": "schema:Affiliation",
    "rdfs:label": "MyAffiliation"
    }
}"""
        with open('test.json', 'w') as f:
            f.write(test_data)

        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), source='test.json')

        h5tbx.dumps('test.hdf')

        pathlib.Path('test.json').unlink(missing_ok=True)
        h5.hdf_filename.unlink(missing_ok=True)

    def test_codemeta_to_hdf(self):
        codemeta_filename = __this_dir__ / '../../codemeta.json'

        data = ontolutils.dquery('schema:SoftwareSourceCode',
                                 codemeta_filename,
                                 context={'schema': 'http://schema.org/'})

        self.assertIsInstance(data, list)
        self.assertTrue(len(data) == 1)
        self.assertTrue(data[0]['version'] == __version__)
        self.assertTrue('author' in data[0])
        self.assertIsInstance(data[0]['author'], list)
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), data=data[0])
            from h5rdmtoolbox import consts
            self.assertEqual(h5['person']['author1'].attrs[consts.IRI_PREDICATE_ATTR_NAME]['SELF'],
                             'http://schema.org/author')

        h5tbx.dumps('test.hdf')

        h5.hdf_filename.unlink(missing_ok=True)
