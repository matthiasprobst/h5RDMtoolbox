import pathlib
import sys
import unittest
from contextlib import contextmanager

import numpy as np
import rdflib
import requests
from ontolutils.ex import dcat

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.catalog import Query, QueryResult, SparqlQuery, RemoteSparqlQuery, RemoteSparqlStore, StoreManager, \
    DataStore, \
    InMemoryRDFStore, GraphDB
from h5rdmtoolbox.catalog.stores.hdf5_store import HDF5Store

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

    def _upload_file(self, filename, skip_unsupported: bool = False) -> bool:
        return True

    def execute_query(self, query: Query):
        raise NotImplementedError("CSVDatabase does not support queries.")


class SimpleHDF5Store(HDF5Store):

    def __init__(self, data_directory):
        super().__init__(data_directory)
        self.data_directory = pathlib.Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self._downloaded_files = {}

    def _get_or_download_file(self, download_url: str) -> pathlib.Path:
        """Download HDF5 file if not already present."""
        file_info = self._file_registry.get(download_url)
        if not file_info:
            raise FileNotFoundError(f"File {download_url} not registered in store")

        filename = file_info["filename"]
        local_filename = self.data_directory / file_info["filename"]
        if local_filename.exists():
            return local_filename

        # download to target directory
        dist = dcat.Distribution(
            download_URL=file_info["download_url"]
        )
        return dist.download(
            dest_filename=local_filename,
        )

    @contextmanager
    def open_hdf5_object(
            self,
            download_url: str,
            object_name: str = None):
        """Open HDF5 file and return object using context manager."""
        local_path = self._get_or_download_file(download_url)
        with h5tbx.File(local_path, "r") as f:
            if object_name is None:
                yield f["/"]
            else:
                yield f[object_name] if object_name in f else None


def create_test_hdf5_file():
    """Create a test HDF5 file for demonstration."""

    with h5tbx.File() as f:
        # Create test datasets
        f.create_dataset("temperature", data=np.random.rand(10, 5) * 25 + 273.15)
        f.create_dataset("pressure", data=np.random.rand(10, 5) * 1000 + 101325)

        # Create groups
        group = f.create_group("measurements")
        group.create_dataset("humidity", data=np.random.rand(10, 5) * 100)

        # Add metadata
        f.attrs["title"] = "Test Dataset"
        f.attrs["created"] = "2024-01-01"
        f["temperature"].attrs["units"] = "K"
        f["pressure"].attrs["units"] = "Pa"

    return f.hdf_filename


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

    def test_hdf_store(self):
        # print("Creating test HDF5 file...")
        # hdf5_filename = create_test_hdf5_file()
        # print(f"Created: {hdf5_filename}")
        #
        # print("\n1. Setting up HDF5 store...")
        working_dir = __this_dir__ / "local-db/hdf"
        hdf5_store = SimpleHDF5Store(working_dir)
        #
        # # insert_result = hdf5_store._upload_file(
        # #     download_url=hdf5_filename.as_uri(),
        # #     filename=hdf5_filename
        # # )
        # insert_result = hdf5_store._upload_file(
        #     download_url="https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-05-20_run.hdf/content",
        #     filename=hdf5_filename
        # )
        # self.assertEqual(
        #     insert_result,
        #     {
        #         "local_path": None,
        #         "filename": hdf5_filename,
        #         "downloaded": False,
        #         "download_url": hdf5_filename.as_uri(),
        #     }
        # )
        #
        # query_result = {
        #     "identifier": "test_dataset_001",
        #     "download_url": hdf5_filename.as_uri(),
        #     "hdf_name": "/temperature",  # This is the key information!
        # }

        download_URL = "https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-05-20_run.hdf/content"
        hdf5_store.upload_file(
            distribution=dcat.Distribution(
                id=download_URL,
                download_URL=download_URL,
                title="Test HDF5 Dataset",
            )
        )

        # a RDF query on the RDF store would return a distribution and a dataset
        # --> ready to use SPARQL: get_distribution_to_hdf_dataset(hdf_dataset_uri: str)

        with hdf5_store.open_hdf5_object(
                download_url=download_URL,
                object_name="/dp_sm"
        ) as dataset:
            print(f"Dataset shape: {dataset.shape}")
            print(f"Dataset dtype: {dataset.dtype}")
            print(f"First 5 values: {dataset[:5]}")
            print(f"Units: {dataset.attrs.get('units', 'N/A')}")
