"""Test the finding objects based on rdf"""
import unittest

from rdflib import FOAF

import h5rdmtoolbox as h5tbx


class TestQueryRDF(unittest.TestCase):

    def test_find_rdf(self):
        with h5tbx.File() as h5:
            h5.attrs['first_name', FOAF.firstName] = 'John'

            grp = h5.create_group('person')
            grp.attrs['first_name', FOAF.firstName] = 'Jane'

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_predicate=FOAF.firstName,
                                      recursive=False)

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].attrs['first_name'], 'John')

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_subject=FOAF.firstName,
                                      recursive=False)
        self.assertEqual(len(res), 0)

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_predicate=FOAF.firstName,
                                      recursive=True)
        self.assertEqual(len(res), 2)
        sorted_res = sorted(res)
        self.assertEqual(sorted_res[1].attrs['first_name'], 'Jane')
        self.assertEqual(sorted_res[0].attrs['first_name'], 'John')
