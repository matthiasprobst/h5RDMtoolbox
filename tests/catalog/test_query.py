import pathlib
import unittest
import urllib.error

import pytest
import rdflib

from h5rdmtoolbox.catalog import (
    Query,
    QueryResult,
    SparqlQuery,
    RemoteSparqlQuery,
    InMemoryRDFStore,
    RemoteSparqlStore,
)
from h5rdmtoolbox.catalog.utils import sparql_result_to_df

__this_dir__ = pathlib.Path(__file__).parent.resolve()


def skip_transient_wikidata_error(exc):
    """Skip live WDQS tests when the public service throttles or is unavailable."""
    if isinstance(exc, urllib.error.HTTPError) and exc.code in {429, 503}:
        pytest.skip(f"Wikidata Query Service unavailable: HTTP {exc.code}")
    if isinstance(exc, urllib.error.URLError):
        pytest.skip(f"Wikidata Query Service unavailable: {exc}")
    raise exc


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
            'SparqlQuery(query="SELECT * WHERE { ?s ?p ?o }", description="")',
        )
        store = InMemoryRDFStore(data_dir=__this_dir__ / "testdata")
        res = SparqlQuery("SELECT * WHERE { ?s ?p ?o }").execute(store)
        self.assertIsInstance(res, QueryResult)
        self.assertEqual(res.query, sparql_query)
        self.assertEqual(res.derived_graph, None)
        self.assertTrue(
            res.data.equals(
                sparql_result_to_df(graph.query("SELECT * WHERE { ?s ?p ?o }"))
            )
        )

    @pytest.mark.wikidata
    def test_wikidata_query(self):
        # User-Agent header is now set by RemoteSparqlStore
        endpoint_url = "https://query.wikidata.org/sparql"
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
            f'RemoteSparqlQuery(query="{query_str}", description="")',
        )
        remote_store = RemoteSparqlStore(
            endpoint_url=endpoint_url, return_format="json"
        )

        try:
            res = sparql_query.execute(remote_store)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            skip_transient_wikidata_error(exc)
        self.assertIsInstance(res, QueryResult)
        self.assertEqual(res.query, sparql_query)
        self.assertTrue(len(res.data) >= 917)

        sparql_query = RemoteSparqlQuery(query="DESCRIBE wd:Q131448345")
        remote_store = RemoteSparqlStore(
            endpoint_url=endpoint_url, return_format="json-ld"
        )
        try:
            res = sparql_query.execute(remote_store)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            skip_transient_wikidata_error(exc)
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
