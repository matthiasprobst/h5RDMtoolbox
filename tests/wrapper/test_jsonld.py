import h5py
import json
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
import ontolutils
from h5rdmtoolbox import __version__
from h5rdmtoolbox.wrapper import jsonld
from h5rdmtoolbox.wrapper import rdf
from ontolutils import namespaces, urirefs, Thing

logger = h5tbx.logger
# logger.setLevel('ERROR')
__this_dir__ = pathlib.Path(__file__).parent


class TestCore(unittest.TestCase):

    def test_dump_hdf_to_json(self):
        """similar yet different to https://hdf5-json.readthedocs.io/en/latest/index.html"""
        with h5py.File('test.hdf', 'w') as h5:
            h5.attrs['version'] = __version__

        # def dump_hdf_to_json(h5_filename):
        with h5py.File('test.hdf', 'r') as h5:
            print(jsonld.dumps(h5))

    def test_dump_hdf_to_json2(self):
        @namespaces(foaf='http://xmlns.com/foaf/0.1/',
                    prov='http://www.w3.org/ns/prov#')
        @urirefs(Person='prov:Person',
                 name='foaf:firstName',
                 lastName='foaf:lastName')
        class Person(Thing):
            name: str = None
            lastName: str

        p = Person(name='John', lastName='Doe')

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(h5.create_group('contact'),
                          data=json.loads(p.model_dump_jsonld()),
                          predicate='m4i:contact')
            h5.dumps()

    def test_jsonld_dumps(self):
        sn_iri = 'https://matthiasprobst.github.io/ssno/#standard_name'
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('test_dataset', shape=(3,))
            grp = h5.create_group('grp')
            grp.attrs['test', sn_iri] = 'test'
            sub_grp = grp.create_group('Fan')
            sub_grp.create_dataset('D3', data=300)
            sub_grp['D3'].attrs['units', 'http://w3id.org/nfdi4ing/metadata4ing#hasUnits'] = 'mm'
            sub_grp['D3'].rdf['units'].object = 'https://qudt.org/vocab/unit/MilliM'
            sub_grp['D3'].attrs['standard_name', sn_iri] = 'blade_diameter3'
            h5.dumps()
        from pprint import pprint
        out = h5tbx.jsonld.dumpd(h5.hdf_filename,
                                 context={'schema': 'http://schema.org/',
                                          "ssno": "https://matthiasprobst.github.io/ssno/#",
                                          "m4i": "http://w3id.org/nfdi4ing/metadata4ing#"})
        pprint(out)
        found_m4iNumericalVariable = False
        for graph in out['@graph']:
            if graph['@type'] == 'm4i:NumericalVariable':
                self.assertEqual(graph['m4i:hasUnits'], 'mm')
                self.assertEqual(graph['ssno:standard_name'], 'blade_diameter3')
                found_m4iNumericalVariable = True
        self.assertTrue(found_m4iNumericalVariable)

    def test_to_hdf(self):
        test_data = """{"@context": {"foaf": "http://xmlns.com/foaf/0.1/", "prov": "http://www.w3.org/ns/prov#",
"schema": "http://www.w3.org/2000/01/rdf-schema#",
 "schema": "http://schema.org/",
 "local": "http://example.org/"},
"@id": "local:testperson",
"@type": "prov:Person",
"foaf:firstName": "John",
"foaf:lastName": "Doe",
"age": 21,
"schema:affiliation": {
    "@id": "Nef657ff40e464dd09580db3f32de2cf1",
    "@type": "schema:Organization",
    "rdfs:label": "MyAffiliation"
    }
}"""
        with open('test.json', 'w') as f:
            f.write(test_data)

        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), source='test.json')
            self.assertTrue('person' in h5)
            self.assertTrue('firstName' in h5['person'].attrs)
            self.assertTrue('lastName' in h5['person'].attrs)
            self.assertEqual(h5['person'].attrs['firstName'], 'John')
            self.assertEqual(h5['person'].attrs['age'], 21)

        h5tbx.dumps('test.hdf')

        print(
            h5tbx.jsonld.dumps(
                h5.hdf_filename, indent=2,
                context={"m4i": "http://w3id.org/nfdi4ing/metadata4ing#"}
            )
        )

        pathlib.Path('test.json').unlink(missing_ok=True)
        h5.hdf_filename.unlink(missing_ok=True)

    def test_codemeta_to_hdf(self):
        codemeta_filename = __this_dir__ / '../../codemeta.json'

        data = ontolutils.dquery(
            'schema:SoftwareSourceCode',
            codemeta_filename,
            context={'schema': 'http://schema.org/'})  # Note, that codemeta uses the unsecure http

        self.assertIsInstance(data, list)
        self.assertTrue(len(data) == 1)
        self.assertTrue(data[0]['version'] == __version__)
        self.assertTrue('author' in data[0])
        self.assertIsInstance(data[0]['author'], list)
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), data=data[0])
            self.assertEqual(h5['person']['author1'].attrs[rdf.RDF_PREDICATE_ATTR_NAME]['SELF'],
                             'http://schema.org/author')

        h5tbx.dumps('test.hdf')

        h5.hdf_filename.unlink(missing_ok=True)
