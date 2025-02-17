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
            grp.attrs['fname', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'
            h5.dumps()

        ret = h5tbx.dump_jsonld(h5.hdf_filename,
                                structural=False,
                                compact=False,
                                context={'foaf': 'http://xmlns.com/foaf/0.1/'})
        jsondict = json.loads(ret)
        entries = jsondict["@graph"]
        found_foaf_first_name = False
        for e in entries:
            if e.get("@type", None) == "prov:Person":
                self.assertEqual(e['foaf:firstName'], 'John')
                found_foaf_first_name = True
                break
        self.assertTrue(found_foaf_first_name)

        ret = h5tbx.dump_jsonld(h5.hdf_filename,
                                structural=True,
                                compact=False)
        jsondict = json.loads(ret)
        verified_types = False
        for g in jsondict['@graph']:
            if g.get('foaf:firstName', None) == 'John':
                verified_types = True
                self.assertEqual(sorted(g['@type']), sorted(['hdf:Group', 'prov:Person']))
        self.assertTrue(verified_types)

        with self.assertRaises(ValueError):
            h5tbx.dump_jsonld(h5.hdf_filename, structural=False, semantic=False)

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
