import logging
import pathlib
import sys
import unittest
from typing import List

from ontolutils.ex import dcat, prov

from h5rdmtoolbox.catalog import Catalog, QueryResult, FederatedQueryResult, SparqlQuery, RDFStore, DataStore, \
    MetadataStore

logger = logging.getLogger("h5rdmtoolbox")
logger.setLevel(logging.DEBUG)
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

__this_dir__ = pathlib.Path(__file__).parent

sys.path.insert(0, str(__this_dir__))
from h5rdmtoolbox.catalog import InMemoryRDFStore
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
    _store: RDFStore = db.rdf_store
    results = SparqlQuery(sparql_query).execute(_store)

    # result_data = [{str(k): parse_literal(v) for k, v in binding.items()} for binding in results.data.bindings]

    federated_query_results = []

    rdf_database = db.rdf_store
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

        oraga = prov.Organization(
            id="https://ror.org/04t3en479",
            name="Institute of thermal Turbomachinery (ITS), Karlsruhe Institute of Technology@en",
            url="https://www.its.kit.edu/english/index.php",
            ror_id="https://ror.org/04t3en479")
        creator = prov.Person(
            id="https://orcid.org/0000-0001-8729-0482",
            first_name="Matthias",
            last_name="Probst",
            orcid_id="https://orcid.org/0000-0001-8729-0482",
            affiliation=oraga
        )

        catalog = dcat.Catalog(
            id="https://example.org/catalogs/test_catalog",
            title="Test Catalog",
            description="A test catalog for unit testing.",
            creator=creator,
            primaryTopic="https://www.wikidata.org/entity/Q137561830",
            dataset=[
                dcat.Dataset(
                    id="https://handle.test.datacite.org/10.5072/zenodo.411647",
                    title="Dataset 1",
                    description="First test dataset.",
                    identifier="2023-11-07-14-03-39_run",
                    distribution=[
                        dcat.Distribution(
                            id="https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.hdf/content",
                            title="2023-11-07-14-03-39_run.hdf",
                            downloadURL="https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.hdf/content",
                            mediaType="https://www.iana.org/assignments/media-types/application/x-hdf"
                        ),
                        dcat.Distribution(
                            id="https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.ttl/content",
                            title="2023-11-07-14-03-39_run.ttl",
                            downloadURL="https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.ttl/content",
                            mediaType="https://www.iana.org/assignments/media-types/text/turtle"
                        )
                    ]
                )
            ]
        )
        catalog_file = __this_dir__ / "catalog.ttl"
        with open(catalog_file, "w", encoding="utf-8") as f:
            f.write(catalog.serialize(format="ttl"))

        in_memory_store = InMemoryRDFStore(__this_dir__ / "data")

        working_dir = __this_dir__ / "local-db"
        working_dir.mkdir(exist_ok=True)

        db = Catalog(
            catalog,
            rdf_store=in_memory_store,
            hdf_store=CSVDatabase(),
            working_directory=working_dir,
            add_wikidata_store=True,
            augment_wikidata_knowledge=True
        )
        self.assertIsInstance(db.catalog, dcat.Catalog)
        db = Catalog(
            catalog_file,
            rdf_store=in_memory_store,
            hdf_store=CSVDatabase(),
            working_directory=working_dir
        )
        self.assertIsInstance(db.catalog, dcat.Catalog)
        # return
        # db = Catalog(
        #     metadata_store=InMemoryRDFStore(__this_dir__ / "data"),
        #     hdf_store=CSVDatabase()
        # )

        rdf_database: RDFStore = db.rdf_store
        hdf_store: DataStore = db.hdf_store

        self.assertEqual(391, len(db.rdf_store.graph))

        self.assertIsInstance(rdf_database, MetadataStore)
        self.assertIsInstance(rdf_database, InMemoryRDFStore)
        self.assertIsInstance(hdf_store, DataStore)
        self.assertIsInstance(hdf_store, CSVDatabase)

        hdf_store = db.hdf_store
        rdf_database = db.rdf_store
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
