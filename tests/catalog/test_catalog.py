import logging
import pathlib
import sys
import unittest
from typing import List

from ontolutils.ex import dcat

from h5rdmtoolbox.catalog import CatalogManager, QueryResult, FederatedQueryResult, SparqlQuery, RDFStore, DataStore, \
    MetadataStore

logger = logging.getLogger("h5rdmtoolbox")
logger.setLevel(logging.DEBUG)
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

__this_dir__ = pathlib.Path(__file__).parent

sys.path.insert(0, str(__this_dir__))
from h5rdmtoolbox.catalog import InMemoryRDFStore, _query_catalog_from_rdf_store
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
    _store: RDFStore = db.main_rdf_store
    results = SparqlQuery(sparql_query).execute(_store)

    # result_data = [{str(k): parse_literal(v) for k, v in binding.items()} for binding in results.data.bindings]

    federated_query_results = []

    rdf_database = db.main_rdf_store
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

    def test_dcat_catalog_read_and_write(self):
        catalog_ttl = __this_dir__ / "data/catalog.ttl"
        self.assertTrue(catalog_ttl.exists())

        working_dir = __this_dir__ / "local-db"
        working_dir.mkdir(parents=True, exist_ok=True)

        cm = CatalogManager(
            catalog=catalog_ttl,
            working_directory=working_dir
        )
        with self.assertRaises(KeyError):
            cm.download_metadata()

        in_memory_store = InMemoryRDFStore(cm.rdf_directory)
        cm.add_main_rdf_store(in_memory_store)
        cm.download_metadata()
        cm.main_rdf_store.populate()

        cat = _query_catalog_from_rdf_store(in_memory_store)
        ttl = cat.serialize("ttl")

        self.assertEqual(ttl, """@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix m4i: <http://w3id.org/nfdi4ing/metadata4ing#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix schema: <https://schema.org/> .

<https://example.org/catalogs/test_catalog> a dcat:Catalog ;
    dcterms:creator <https://orcid.org/0000-0001-8729-0482> ;
    dcterms:description "A test catalog for unit testing." ;
    dcterms:title "Test Catalog" ;
    dcat:dataset <https://handle.test.datacite.org/10.5072/zenodo.411647>,
        <https://handle.test.datacite.org/10.5072/zenodo.411652> ;
    dcat:version "1.0.0" .

<https://handle.test.datacite.org/10.5072/zenodo.411647> a dcat:Dataset ;
    dcterms:description "First test dataset." ;
    dcterms:identifier "2023-11-07-14-03-39_run" ;
    dcterms:title "Dataset 1" ;
    dcat:distribution <https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.hdf/content>,
        <https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.ttl/content> .

<https://handle.test.datacite.org/10.5072/zenodo.411652> a dcat:Dataset ;
    dcterms:description "First test dataset." ;
    dcterms:identifier "2023-11-07-18-45-45_run" ;
    dcterms:title "Dataset 2" ;
    dcat:distribution <https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.hdf/content>,
        <https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.ttl/content> .

<https://orcid.org/0000-0001-8729-0482> a prov:Person ;
    m4i:orcidId <https://orcid.org/0000-0001-8729-0482> ;
    foaf:firstName "Matthias" ;
    foaf:lastName "Probst" ;
    schema:affiliation <https://ror.org/04t3en479> .

<https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.hdf/content> a dcat:Distribution ;
    dcterms:title "2023-11-07-14-03-39_run.hdf" ;
    dcat:downloadURL <https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.hdf/content> ;
    dcat:mediaType <https://www.iana.org/assignments/media-types/application/x-hdf> .

<https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.ttl/content> a dcat:Distribution ;
    dcterms:title "2023-11-07-14-03-39_run.ttl" ;
    dcat:downloadURL <https://sandbox.zenodo.org/api/records/411647/files/2023-11-07-14-03-39_run.ttl/content> ;
    dcat:mediaType <https://www.iana.org/assignments/media-types/text/turtle> .

<https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.hdf/content> a dcat:Distribution ;
    dcterms:title "2023-11-07-18-45-45_run.hdf" ;
    dcat:downloadURL <https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.hdf/content> ;
    dcat:mediaType <https://www.iana.org/assignments/media-types/application/x-hdf> .

<https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.ttl/content> a dcat:Distribution ;
    dcterms:title "2023-11-07-18-45-45_run.ttl" ;
    dcat:downloadURL <https://sandbox.zenodo.org/api/records/411652/files/2023-11-07-18-45-45_run.ttl/content> ;
    dcat:mediaType <https://www.iana.org/assignments/media-types/text/turtle> .

""")

    def test_rdf_and_csv_stores(self):
        working_dir = __this_dir__ / "local-db"
        working_dir.mkdir(parents=True, exist_ok=True)

        catalog_ttl = __this_dir__ / "data/catalog.ttl"

        if working_dir.exists():
            cm = CatalogManager(
                working_directory=working_dir
            )
            in_memory_store = InMemoryRDFStore(cm.rdf_directory, formats="ttl")
            cm.add_main_rdf_store(in_memory_store)
        else:
            cm = CatalogManager(
                catalog=catalog_ttl,
                working_directory=working_dir
            )
            in_memory_store = InMemoryRDFStore(cm.rdf_directory, formats="ttl")
            cm.add_main_rdf_store(in_memory_store)
            cm.download_metadata()
            cm.main_rdf_store.populate()

        cm.add_hdf_store(CSVDatabase())
        if sys.version_info.minor == 12:
            # skip adding wikidata store on non-3.12 Python to avoid rate limiting
            cm.add_wikidata_store(augment_knowledge=True)

        self.assertIsInstance(cm.catalog, dcat.Catalog)

        main_rdf_store: RDFStore = cm.main_rdf_store
        hdf_store: DataStore = cm.hdf_store

        self.assertEqual(4785, len(cm.main_rdf_store.graph))

        self.assertIsInstance(main_rdf_store, MetadataStore)
        self.assertIsInstance(main_rdf_store, InMemoryRDFStore)
        self.assertIsInstance(hdf_store, DataStore)
        self.assertIsInstance(hdf_store, CSVDatabase)

        hdf_store = cm.hdf_store
        main_rdf_store = cm.main_rdf_store
        self.assertIsInstance(hdf_store, CSVDatabase)
        self.assertIsInstance(main_rdf_store, InMemoryRDFStore)

        with self.assertRaises(ValueError):
            main_rdf_store.upload_file(__this_dir__ / "data/data1.jsonld")
        main_rdf_store._expected_file_extensions = {".jsonld", ".ttl", }
        main_rdf_store.upload_file(__this_dir__ / "data/data1.jsonld")

        query = SparqlQuery(query="SELECT * WHERE {?s ?p ?o}", description="Selects all triples")
        res = query.execute(main_rdf_store)
        self.assertEqual(res.description, "Selects all triples")
        self.assertIsInstance(res, QueryResult)

        res = cm.execute_query(query)
        self.assertEqual(res.description, "Selects all triples")

        self.assertIsInstance(res, QueryResult)
        self.assertEqual(4793, len(res.data))

        main_rdf_store.upload_file(__this_dir__ / "data/metadata.jsonld")

        hdf_store.upload_file(__this_dir__ / "data/random_data.csv")
        hdf_store.upload_file(__this_dir__ / "data/random_data.csv")
        hdf_store.upload_file(__this_dir__ / "data/temperature.csv")
        hdf_store.upload_file(__this_dir__ / "data/users.csv")

        data = get_temperature_data_by_date(cm, date="2024-01-01")
        self.assertIsInstance(data, list)
        self.assertIsInstance(data[0], FederatedQueryResult)

        self.assertTrue((cm.rdf_directory / "data1.jsonld").exists())
        self.assertTrue((cm.rdf_directory / "metadata.jsonld").exists())

        (cm.rdf_directory / "data1.jsonld").unlink()
        (cm.rdf_directory / "metadata.jsonld").unlink()
