import pathlib
import sys
import unittest

import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON

from h5rdmtoolbox.catalog import Query, QueryResult, SparqlQuery, RemoteSparqlQuery, InMemoryRDFStore, RemoteSparqlStore
from h5rdmtoolbox.catalog.utils import sparql_result_to_df

__this_dir__ = pathlib.Path(__file__).parent.resolve()

TESTING_VERSIONS = (12,)


def get_python_version():
    """Get the current Python version as a tuple."""
    return sys.version_info.major, sys.version_info.minor, sys.version_info.micro


class TestQuery(unittest.TestCase):

    def test_query(self):
        class SQLQuery(Query):

            def execute(self) -> QueryResult:
                return QueryResult(self, data="result", description=self.description)

        q = SQLQuery("SELECT * FROM Customers;", "Get all customers")
        res = q.execute()
        self.assertEqual(res.query, q)
        self.assertEqual(res.description, "Get all customers")

        res = SQLQuery("SELECT * FROM Customers;", "Get all customers").execute()
        self.assertIsInstance(res, QueryResult)

    def test_sparql_query(self):
        graph = rdflib.Graph()
        sparql_query = SparqlQuery(query="SELECT * WHERE { ?s ?p ?o }")
        self.assertEqual(
            sparql_query.__repr__(),
            'SparqlQuery(query="SELECT * WHERE { ?s ?p ?o }", description="")'
        )
        store = InMemoryRDFStore(data_dir=__this_dir__ / "testdata")
        res = SparqlQuery("SELECT * WHERE { ?s ?p ?o }").execute(store)
        self.assertIsInstance(res, QueryResult)
        self.assertEqual(res.query, sparql_query)
        self.assertEqual(res.derived_graph, None)
        self.assertTrue(res.data.equals(sparql_result_to_df(graph.query("SELECT * WHERE { ?s ?p ?o }"))))

    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason=f"Only test on Python {TESTING_VERSIONS}")
    def test_wikidata_query(self):
        enpoint_url = "https://query.wikidata.org/sparql"
        sparql_wrapper = SPARQLWrapper(enpoint_url)
        sparql_wrapper.setReturnFormat(JSON)
        query_str = """
SELECT * WHERE {
  wd:Q131448345 ?property ?value.
  OPTIONAL { ?value rdfs:label ?valueLabel. }
}
ORDER BY ?propertyLabel
"""
        sparql_query = RemoteSparqlQuery(query_str)
        self.assertEqual(
            sparql_query.__repr__(),
            f"RemoteSparqlQuery(query=\"{query_str}\", description=\"\")"
        )
        remote_store = RemoteSparqlStore(endpoint_url=enpoint_url, return_format="json")

        res = sparql_query.execute(remote_store)
        self.assertIsInstance(res, QueryResult)
        self.assertEqual(res.query, sparql_query)
        self.assertTrue(len(res.data) >= 917)

        sparql_query = RemoteSparqlQuery(query="DESCRIBE wd:Q131448345")
        remote_store = RemoteSparqlStore(endpoint_url=enpoint_url, return_format="json-ld")
        res = sparql_query.execute(remote_store)
        print(res.data.serialize("json-ld").serialize())

    def test_construct_query(self):
        # g = rdflib.Graph()
        # g.parse(__this_dir__ / "data" / "planets.ttl", format="turtle")
        construct_query = """
        PREFIX ex: <http://example.org/schema/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        CONSTRUCT {
          ?planet a ex:Planet ;
                  ex:mass ?mass ;
                  ex:radius ?radius ;
                  ex:label ?label .
        }
        WHERE {
          ?planet a ex:Planet ;
                  ex:mass ?mass ;
                  ex:radius ?radius .
          OPTIONAL {
            ?planet rdfs:label ?label .
            FILTER(LANG(?label) = "en")
          }
        }
        """

        sparql_query = SparqlQuery(query=construct_query)
        store = InMemoryRDFStore(data_dir=__this_dir__ / "data")
        store.populate()
        res = sparql_query.execute(store)

        self.assertEqual(16, len(res.derived_graph))

        select_query = """
        PREFIX ex: <http://example.org/schema/>

        SELECT ?planet ?mass ?radius ?label
        WHERE {
          ?planet a ex:Planet ;
                  ex:mass ?mass ;
                  ex:radius ?radius .
          OPTIONAL { ?planet ex:label ?label }

          FILTER(?mass > 1.0e24)
        }
        ORDER BY DESC(?mass)
        """
        self.assertEqual(3, len(res.derived_graph.query(select_query)))
