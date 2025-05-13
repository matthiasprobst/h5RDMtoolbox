"""Testing dumping functionality"""
import json
import unittest

from rdflib import PROV, FOAF

import h5rdmtoolbox as h5tbx


class TestDump(unittest.TestCase):

    def test_dump_jsonld(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('Person')
            grp.rdf.type = PROV.Person
            grp.rdf.subject = "https://orcid.org/123"
            grp.attrs['fname', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'
            h5.dumps()

        ret = h5tbx.dump_jsonld(h5.hdf_filename,
                                structural=False,
                                compact=False,
                                context={'foaf': 'http://xmlns.com/foaf/0.1/'})
        jsondict = json.loads(ret)

        for v in jsondict['@graph']:
            if v.get("@type") == 'prov:Person':
                person_data = v
                break
        self.assertEqual(person_data['@type'], 'prov:Person')
        self.assertEqual(person_data['foaf:firstName'], 'John')
        self.assertEqual(person_data['foaf:lastName'], 'Doe')

        ret = h5tbx.dump_jsonld(h5.hdf_filename,
                                structural=True,
                                compact=False)
        jsondict = json.loads(ret)
        verified_types = False
        for g in jsondict['@graph']:
            if g.get('foaf:firstName', None) == 'John':
                verified_types = True
                self.assertEqual(g['@type'], 'prov:Person')
        self.assertTrue(verified_types)

        with self.assertRaises(ValueError):
            h5tbx.dump_jsonld(h5.hdf_filename, structural=False, semantic=False)

    def test_dump_serialized_dict_with_urls(self):
        with h5tbx.File() as h5:
            h5.attrs["metadata"] = json.dumps({
                "title": "My title",
                "description": "My description",
                "url": "https://example.com",
                "doi": "https://zenodo.org/records/13182574",
            })
            h5.dump()

    def test_dump_structural_true_semantic_false(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('Person')
            grp.rdf.type = PROV.Person
            grp.attrs['fname', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'

        jsonld_str = h5tbx.dump_jsonld(h5.hdf_filename, structural=True, semantic=False)
        print(jsonld_str)

    def test_sdump(self):
        h5tbx.use(None)

        print('\n---------------\n')
        with h5tbx.File() as h5:
            h5.create_dataset('myvar', data=[1, 2, 4], attrs={'units': 'm/s', 'long_name': 'test var'})
            h5.sdump()

        print('\n---------------\n')
        with h5tbx.File() as h5:
            h5.create_dataset('myvar', data=[1, 2, 4], attrs={'units': 'm/s', 'long_name': 'test var'})
            h5.sdump()
