import pathlib
import sys
import unittest

import rdflib

from h5rdmtoolbox.catalog import Query, QueryResult, SparqlQuery, RemoteSparqlQuery, RemoteSparqlStore, StoreManager, \
    DataStore, \
    InMemoryRDFStore

__this_dir__ = pathlib.Path(__file__).parent


class MockSqlQuery(Query):

    def __init__(self, query: str, description: str = None):
        # super().__init__(query, description)
        self.query = query

    def execute(self, *args, **kwargs) -> QueryResult:
        return QueryResult(self, "mock_result")


class CSVDatabase(DataStore):

    def __init__(self):
        self._filenames = []
        self.tables = {}
        self._expected_file_extensions = {".csv", }

    # @property
    # def query(self) -> Type[Query]:
    #     return MockSqlQuery

    def upload_file(self, filename, skip_unsupported:bool=False) -> bool:
        return True

    def execute_query(self, query: Query):
        raise NotImplementedError("CSVDatabase does not support queries.")


class TestDataStore(unittest.TestCase):

    def test_DataStoreManager(self):
        manager = StoreManager()
        self.assertEqual(len(manager), 0)
        self.assertEqual(
            manager.__repr__(),
            "StoreManager(stores=[])"
        )

    def test_add_store(self):
        manager = StoreManager()
        store = CSVDatabase()
        self.assertEqual(
            len(manager.stores),
            0
        )
        self.assertEqual(store.__repr__(), "CSVDatabase()")
        manager.add_store("test_store", store)

        self.assertEqual(len(manager), 1)

        with self.assertRaises(AttributeError):
            manager.does_not_exist

    def test_query_store(self):
        store = CSVDatabase()
        query = MockSqlQuery(query="SELECT * FROM test_table;")
        self.assertIsInstance(query, Query)
        self.assertIsInstance(query, MockSqlQuery)
        self.assertEqual(query.query, "SELECT * FROM test_table;")

        qres = query.execute(store)
        self.assertIsInstance(qres, QueryResult)
        self.assertEqual(qres.data, "mock_result")

    def test_wikidata_store(self):
        if not (sys.version_info.major == 3 and sys.version_info.minor == 12):
            self.skipTest("Skipping test on non-3.12 Python to avoid rate limiting")
        remote_store = RemoteSparqlStore("https://query.wikidata.org/sparql", return_format="json")
        self.assertIsInstance(remote_store, RemoteSparqlStore)

        sparql_query = """
SELECT * WHERE {
  wd:Q131549102 ?property ?value.
  OPTIONAL { ?value rdfs:label ?valueLabel. }
}
ORDER BY ?propertyLabel
"""
        query = RemoteSparqlQuery(sparql_query)
        res = query.execute(remote_store)
        self.assertTrue(len(res.data) >= 172)

    def test_InMemoryRDFStore(self):
        ims = InMemoryRDFStore(
            data_dir=__this_dir__ / "data",
            recursive_exploration=True,
            formats=["ttl"]
        )
        ims.populate()
        self.assertEqual(
            {".ttl"},
            ims._expected_file_extensions
        )
        self.assertIsInstance(ims, InMemoryRDFStore)
        filenames = ims.filenames

        self.assertEqual(2, len(filenames))
        for filename in filenames:
            self.assertTrue(filename.suffix in ims._expected_file_extensions)
        self.assertIsInstance(ims.graph, rdflib.Graph)

        # get the radius of planet with rdfs:label "Earth"
        sparql_query = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/schema/>
        
SELECT ?radius
WHERE {
  ?planet a ex:Planet ;
          rdfs:label ?label ;
          ex:radius ?radius .

  FILTER(STR(?label) = "Earth")
}
"""
        rsq = RemoteSparqlQuery(sparql_query)
        with self.assertRaises(TypeError):
            rsq.execute(ims)  # should raise TypeError since rsq is RemoteSparqlQuery

        sq = SparqlQuery(sparql_query)
        res = sq.execute(ims)
        self.assertEqual(1, len(res.data))
        radius_value = res.data['radius'][0]
        self.assertEqual(6371000.0, radius_value)
