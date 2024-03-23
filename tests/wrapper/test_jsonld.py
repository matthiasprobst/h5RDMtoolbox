import json
import pathlib
import rdflib
import unittest

import h5rdmtoolbox as h5tbx
import ontolutils
from h5rdmtoolbox import __version__
from h5rdmtoolbox.wrapper import jsonld
from h5rdmtoolbox.wrapper import rdf
from ontolutils import namespaces, urirefs, Thing

logger = h5tbx.logger

__this_dir__ = pathlib.Path(__file__).parent


class TestCore(unittest.TestCase):

    def setUp(self):
        LEVEL = 'WARNING'
        logger.setLevel(LEVEL)
        for h in logger.handlers:
            h.setLevel(LEVEL)

    def tearDown(self):
        pathlib.Path('test.hdf').unlink(missing_ok=True)

    def test_dump_hdf_to_json(self):
        """similar yet different to https://hdf5-json.readthedocs.io/en/latest/index.html"""
        with h5tbx.File(name=None, mode='w') as h5:
            # h5.attrs['test_attr'] = 123
            del h5['h5rdmtoolbox']
            ds = h5.create_dataset('grp/test_dataset',
                                   data=[1, 2, 3],
                                   attrs={'standard_name': 'x_velocity',
                                          'standard_name_non_iri': 'x_velocity',
                                          'unit': 'm/s'})
            from ontolutils import M4I
            ds.rdf.subject = str(M4I.NumericalVariable)
            ds.rdf.predicate['standard_name'] = 'https://matthiasprobst.github.io/ssno#standard_name'
            ds.rdf.object['standard_name'] = 'https://matthiasprobst.github.io/pivmeta#x_velocity'
            ds.rdf.object['standard_name_non_iri'] = 'https://matthiasprobst.github.io/pivmeta#x_velocity'

            ds.attrs['a list'] = [1, 2, 3]
            ds.attrs['a 1D list'] = (1,)

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File(h5.hdf_filename, 'r') as h5:
            json_str = jsonld.dumps(h5, indent=2, compact=False)

        get_all_datasets_with_standard_name = """PREFIX hdf5: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        PREFIX ssno: <https://matthiasprobst.github.io/ssno#>
        
        SELECT  ?name ?sn
        {
            ?obj a hdf5:Dataset .
            ?obj hdf5:name ?name .
            ?obj ssno:standard_name ?sn .
        }"""
        g = rdflib.Graph().parse(data=json_str, format='json-ld')
        qres = g.query(get_all_datasets_with_standard_name)
        self.assertEqual(len(qres), 1)
        for name, sn in qres:
            self.assertEqual(str(name), '/grp/test_dataset')
            self.assertEqual(str(sn), 'https://matthiasprobst.github.io/pivmeta#x_velocity')

    def test_json_to_hdf(self):
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
        sn_iri = 'https://matthiasprobst.github.io/ssno#standard_name'
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
        out_dict = h5tbx.jsonld.dumpd(h5.hdf_filename,
                                      context={'schema': 'http://schema.org/',
                                               "ssno": "https://matthiasprobst.github.io/ssno#",
                                               "m4i": "http://w3id.org/nfdi4ing/metadata4ing#"})
        pprint(out_dict)
        found_m4iNumericalVariable = False
        for g in out_dict['@graph']:
            if g['@type'] == 'm4i:NumericalVariable':
                self.assertDictEqual(g['m4i:hasUnits'], {'@id': 'https://qudt.org/vocab/unit/MilliM'})
                self.assertEqual(g['ssno:standard_name'], 'blade_diameter3')
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

        # print(
        #     h5tbx.jsonld.dumps(
        #         h5.hdf_filename, indent=2,
        #         context={"m4i": "http://w3id.org/nfdi4ing/metadata4ing#"}
        #     )
        # )
        #
        # pathlib.Path('test.json').unlink(missing_ok=True)
        # h5.hdf_filename.unlink(missing_ok=True)

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
