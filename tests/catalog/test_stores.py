import pathlib
import sys
import unittest

import rdflib
import requests

from h5rdmtoolbox.catalog import Query, QueryResult, SparqlQuery, RemoteSparqlQuery, RemoteSparqlStore, StoreManager, \
    DataStore, \
    InMemoryRDFStore, GraphDB

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

    def upload_file(self, filename, skip_unsupported: bool = False) -> bool:
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
        self.assertEqual(6371000.0, radius_value.value)

    def test_upload_triples(self):
        ims = InMemoryRDFStore(data_dir="tmp", recursive_exploration=False)
        ims.upload_triple(
            (rdflib.URIRef("http://example.org/subject"),
             rdflib.URIRef("http://example.org/predicate"),
             rdflib.Literal("object", lang="en")
             )
        )
        self.assertEqual(1, len(ims.graph))
        # query the triple back
        from h5rdmtoolbox.catalog.query_templates import get_properties
        sq = get_properties("http://example.org/subject")
        res = sq.execute(ims)
        self.assertEqual(1, len(res.data))

        self.assertEqual(
            res.data.iloc[0]["value"],
            rdflib.Literal('object', lang='en')
        )

    def test_graphdb(self):
        try:
            gdb = GraphDB(
                endpoint="http://localhost:7201",
                repository="h5rdmtoolbox-sandbox",
                username="admin",
                password="admin"
            )
            gdb.get_repository_info("h5rdmtoolbox-sandbox")
        except requests.exceptions.ConnectionError as e:
            self.skipTest(f"GraphDB not available: {e}")

        # reset repository:
        if gdb.get_repository_info("h5rdmtoolbox-sandbox"):
            gdb.delete_repository("h5rdmtoolbox-sandbox")
        res = gdb.get_or_create_repository(__this_dir__ / "graphdb-config-sandbox.ttl")

        shapes_ttl = """
@prefix ex: <http://example.com/ns#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape
  a sh:NodeShape ;
  sh:targetClass ex:Person ;
  sh:property [
    sh:path ex:age ;
    sh:datatype xsd:integer ;
  ] .
        """

        gdb.register_shacl_shape(name="person shape", shacl_data=shapes_ttl)

        invalid_person_data = """
        @prefix ex: <http://example.com/ns#> .
        
        ex:Bob a ex:Person ;
            ex:age "not_an_integer" .  
        """
        # upload to graphdb
        with open("invalid_person.ttl", "w") as f:
            f.write(invalid_person_data)
        valid_person_data = """
        @prefix ex: <http://example.com/ns#> .
        
        ex:Alice a ex:Person ;
            ex:age 30 .
        """
        with open("valid_person.ttl", "w") as f:
            f.write(valid_person_data)
        gdb.upload_file("valid_person.ttl")
        with self.assertRaises(ValueError):
            gdb.upload_file("invalid_person.ttl")

        pathlib.Path("valid_person.ttl").unlink()
        pathlib.Path("invalid_person.ttl").unlink()

        gdb._upload_triple(
            (rdflib.URIRef("http://example.com/ns#Charlie"),
             rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
             rdflib.URIRef("http://example.com/ns#Person")
             )
        )
        gdb._upload_triple(
            (rdflib.URIRef("http://example.com/ns#Charlie"),
             rdflib.URIRef("http://example.com/ns#age"),
             rdflib.Literal(25, datatype=rdflib.XSD.integer)
             )
        )
        # add a label to charlie
        gdb._upload_triple(
            (rdflib.URIRef("http://example.com/ns#Charlie"),
             rdflib.URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
             rdflib.Literal("Charlie", lang="en")
             )
        )
        # query back Charlie
        from h5rdmtoolbox.catalog.query_templates import get_properties
        sq = get_properties("http://example.com/ns#Charlie")
        res = sq.execute(gdb)
        self.assertEqual(3, len(res.data))
        self.assertEqual(
            res.data.iloc[0]["property"],
            'http://example.com/ns#age'
        )
        self.assertEqual(
            res.data.iloc[0]["value"],
            25
        )

