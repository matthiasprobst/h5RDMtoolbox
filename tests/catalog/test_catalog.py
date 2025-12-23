import logging
import pathlib
import sys
import unittest
from typing import List

from h5rdmtoolbox.catalog import Catalog
from h5rdmtoolbox.catalog.query import QueryResult, FederatedQueryResult, SparqlQuery
from h5rdmtoolbox.catalog.stores import RDFStore, DataStore, MetadataStore

logger = logging.getLogger("h5rdmtoolbox")
logger.setLevel(logging.DEBUG)
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

__this_dir__ = pathlib.Path(__file__).parent

sys.path.insert(0, str(__this_dir__))
from h5rdmtoolbox.catalog.stores import InMemoryRDFStore
from example_storage_db import CSVDatabase


def get_temperature_data_by_date(db, date: str) -> List[FederatedQueryResult]:
    """High-level abstraction for user to find temperature data.
    It is a federated query that combines metadata and data from the RDF and CSV databases."""
    sparql_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>

    SELECT ?dataset ?url
    WHERE {{
      ?dataset a dcat:Dataset .
      ?dataset dcterms:created "{date}" .
      ?dataset dcat:distribution ?distribution .
      ?distribution dcat:downloadURL ?url .
    }}
    """.format(date=date)
    # results = self["rdf_database"].execute_query(SparqlQuery(sparql_query))
    _store: RDFStore = db.stores.rdf_database
    results = SparqlQuery(sparql_query).execute(_store)

    # result_data = [{str(k): parse_literal(v) for k, v in binding.items()} for binding in results.data.bindings]

    federated_query_results = []

    rdf_database = db.stores.rdf_database
    for dataset, url in zip(results.data["dataset"], results.data["url"]):
        filename = str(url).rsplit('/', 1)[-1]

        data = db.stores.hdf_store.get_all(filename)

        # query all metadata for the dataset:
        metadata_sparql = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>

        SELECT ?p ?o
        WHERE {{
          <{dataset}> ?p ?o .
        }}
        """.format(dataset=dataset)
        metadata = SparqlQuery(metadata_sparql).execute(rdf_database)
        federated_query_results.append(FederatedQueryResult(data=data, metadata=metadata))

    return federated_query_results


class TestGenericLinkedDatabase(unittest.TestCase):

    def test_rdf_and_csv_stores(self):
        # with self.assertRaises(TypeError):
        #     Catalog(
        #         stores={
        #             "rdf_database": 2,
        #             "hdf_store": "not_a_store"
        #         }
        #     )

        db = Catalog(
            metadata_stores={"rdf_database": InMemoryRDFStore(__this_dir__ / "data")},
            hdf_store=CSVDatabase()
        )

        rdf_database: RDFStore = db.stores.rdf_database
        hdf_store: DataStore = db.stores.hdf_store

        self.assertEqual(1, len(db.metadata_stores))

        self.assertIsInstance(rdf_database, MetadataStore)
        self.assertIsInstance(rdf_database, InMemoryRDFStore)
        self.assertIsInstance(hdf_store, DataStore)
        self.assertIsInstance(hdf_store, CSVDatabase)

        hdf_store = db.data_stores.hdf_store
        rdf_database = db.metadata_stores.rdf_database
        self.assertIsInstance(hdf_store, CSVDatabase)
        self.assertIsInstance(rdf_database, InMemoryRDFStore)

        rdf_database.upload_file(__this_dir__ / "data/data1.jsonld")

        query = SparqlQuery(query="SELECT * WHERE {?s ?p ?o}", description="Selects all triples")
        res = query.execute(rdf_database)
        self.assertEqual(res.description, "Selects all triples")

        self.assertIsInstance(res, QueryResult)
        print(res.data)
        # self.assertIn(25, sorted([i.get("foaf:age", -1) for i in res.data["@graph"]]))
        # self.assertIn(30, sorted([i.get("foaf:age", -1) for i in res.data["@graph"]]))

        rdf_database.upload_file(__this_dir__ / "data/metadata.jsonld")

        hdf_store.upload_file(__this_dir__ / "data/random_data.csv")
        hdf_store.upload_file(__this_dir__ / "data/random_data.csv")
        hdf_store.upload_file(__this_dir__ / "data/temperature.csv")
        hdf_store.upload_file(__this_dir__ / "data/users.csv")

        data = get_temperature_data_by_date(db, date="2024-01-01")
        self.assertIsInstance(data, list)
        self.assertIsInstance(data[0], FederatedQueryResult)

    def test_validate_config(self):
        res = Catalog.validate_config(__this_dir__ / "test-config.ttl")
        self.assertTrue(res[0])