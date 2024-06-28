"""Testing common functionality across all wrapper classes"""
import json
import unittest
from rdflib import PROV, FOAF

import h5rdmtoolbox as h5tbx


class TestCommon(unittest.TestCase):

    def test_dump_jsonld(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('Person')
            grp.rdf.type = PROV.Person
            grp.attrs['fname', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'
            h5.dumps()

        ret = h5tbx.dump_jsonld(h5.hdf_filename, structural=False, resolve_keys=True, compact=False)
        jsondict = json.loads(ret)
        self.assertEqual(jsondict['foaf:firstName'], 'John')
        self.assertEqual(jsondict['@type'], 'prov:Person')

        ret = h5tbx.dump_jsonld(h5.hdf_filename, structural=False, resolve_keys=False)
        jsondict = json.loads(ret)
        self.assertEqual(jsondict['fname'], 'John')
        self.assertEqual(jsondict['@type'], 'prov:Person')

        ret = h5tbx.dump_jsonld(h5.hdf_filename, structural=True, resolve_keys=False, compact=False)
        jsondict = json.loads(ret)
        verified_types = False
        for g in jsondict['@graph']:
            if g.get('fname', None) == 'John':
                verified_types = True
                self.assertEqual(sorted(g['@type']), sorted(['hdf5:Group', 'prov:Person']))
        self.assertTrue(verified_types)

        with self.assertRaises(ValueError):
            h5tbx.dump_jsonld(h5.hdf_filename, structural=False, semantic=False)

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
