import logging
import pathlib
import shutil
import warnings
from typing import Union, List

import pyshacl
import rdflib
from ontolutils.ex import dcat

from ._initialization import database_initialization, DownloadStatus
from .core import MetadataStore, DataStore, RDFStore, Store, RemoteSparqlStore, StoreManager, HDF5SqlDB, Query, \
    RemoteSparqlQuery, QueryResult, SparqlQuery, GraphDB, InMemoryRDFStore, FederatedQueryResult
from .profiles import MINIMUM_DATASET_SHACL
from ..repository.zenodo import ZenodoRecord

logger = logging.getLogger("h5rdmtoolbox.catalog")


def _parse_catalog(catalog: Union[str, pathlib.Path, ZenodoRecord, dcat.Catalog]) -> dcat.Catalog:
    """Parses the user input to a dcat.Catalog object.

    - If catalog is a filename (str or pathlib.Path), load the catalog from the file.
    - If catalog is a ZenodoRecord, download all TTL files and check which one fulfills the SHACL.
    - If catalog is already a dcat.Catalog, return it as is.
    """
    if isinstance(catalog, dcat.Catalog):
        return catalog
    if isinstance(catalog, str) and catalog.startswith("http"):
        raise NotImplementedError("Loading catalog from URL is not implemented yet.")
    if isinstance(catalog, ZenodoRecord):
        raise NotImplementedError("Loading catalog from ZenodoRecord is not implemented yet.")
    if isinstance(catalog, (str, pathlib.Path)):
        catalog_path = pathlib.Path(catalog)
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog file {catalog} does not exist.")
        catalogs = dcat.Catalog.from_ttl(source=catalog)
        if len(catalogs) > 1:
            raise ValueError(f"Multiple catalogs found in file {catalog}. Expected only one.")
        if len(catalogs) == 0:
            raise ValueError(f"No catalog found in file {catalog}.")
        return catalogs[0]
    raise TypeError(f"Unsupported catalog type: {type(catalog)}")


def _validate_catalog(catalog: dcat.Catalog) -> bool:
    """Validates the catalog against the SHACL shapes."""
    catalog_graph = rdflib.Graph()
    catalog_graph.parse(data=catalog.serialize("ttl"), format="ttl")
    shacl_graph = rdflib.Graph()
    shacl_graph.parse(data=MINIMUM_DATASET_SHACL, format="ttl")
    results = pyshacl.validate(
        data_graph=catalog_graph,
        shacl_graph=shacl_graph,
        inference='rdfs',
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
    )
    conforms, results_graph, results_text = results
    if not conforms:
        warnings.warn("Catalog does not conform to SHACL shapes.")
        print(" > SHACL validation results:")
        print(f" > {results_text}")
    return conforms, results_graph, results_text


from .query_templates import GET_ALL_METADATA_CATALOG_DATASETS
from .utils import WebResource, download


def _download_catalog_datasets(catalog: dcat.Catalog, download_directory: pathlib.Path) -> List[pathlib.Path]:
    """Downloads all datasets in the catalog to the specified directory."""
    g = rdflib.Graph()
    g.parse(data=catalog.serialize("ttl"), format="ttl")

    results = g.query(GET_ALL_METADATA_CATALOG_DATASETS.query)

    list_of_ttl_web_resources = [WebResource(
        download_url=row.download,
        checksum=row.checksumValue,
        title=row.title,
        identifier=row.identifier,
        mediaType="text/turtle"
    ) for row in results]

    print(
        f"Found {len(list_of_ttl_web_resources)} TTL web resources to download. Downloading to {download_directory}...")
    return download(
        download_directory=download_directory,
        web_resources=list_of_ttl_web_resources
    )


class Catalog:
    """Catalog class to manage multiple metadata and data stores.

    Attributes:
        catalog (dcat.Catalog): The DCAT catalog representing the datasets.
        working_directory (pathlib.Path): The working directory for the catalog.
        rdf_directory (pathlib.Path): The directory for RDF files.
        hdf_directory (pathlib.Path): The directory for HDF5 files.
        stores (StoreManager): The store manager containing metadata and data stores.
        rdf_store (RDFStore): The main RDF store in the catalog.
        hdf_store (DataStore): The HDF5 data store in the catalog.
        rdf_stores (Dict[str, RDFStore]): A dictionary of RDF stores in the catalog
    """

    def __init__(
            self,
            catalog: Union[str, pathlib.Path, ZenodoRecord, dcat.Catalog],
            rdf_store: MetadataStore,
            hdf_store: DataStore = None,
            working_directory: Union[str, pathlib.Path] = None,
            add_wikidata_store: bool = False,
            augment_wikidata_knowledge: bool = False,
    ):
        """Initializes the Catalog.

        Parameters:
            catalog (Union[str, pathlib.Path, ZenodoRecord, dcat.Catalog]): The
                DCAT catalog representing the datasets.
            rdf_store (MetadataStore): The main RDF metadata store.
            hdf_store (DataStore, optional): The HDF5 data store. If None
                a default HDF5SqlDB store will be created.
            working_directory (Union[str, pathlib.Path], optional): The
                working directory for the catalog. If None, uses the current
                working directory. Defaults to None.
            add_wikidata_store (bool, optional): Whether to add a Wikidata
                SPARQL store. Defaults to False.
            augment_wikidata_knowledge (bool, optional): Whether to augment the
                main RDF store with knowledge from Wikidata. Defaults to False.
                This will query the rdf store for Wikidata entities and fetch
                additional information from the Wikidata SPARQL endpoint (direct
                properties, labels, descriptions, etc.).


        """
        self._catalog = _parse_catalog(catalog)
        logger.debug("Validating catalog against SHACL shapes...")
        conforms, results_graph, results_text = _validate_catalog(self._catalog)
        if not conforms:
            raise ValueError(f"The provided catalog does not conform to SHACL shapes: {results_text}")
        logger.info("Catalog validation successful.")

        if working_directory is None:
            working_directory = pathlib.Path.cwd()
        self._working_directory = pathlib.Path(working_directory)
        if not self._working_directory.exists():
            raise NotADirectoryError(f"Working directory {self._working_directory} does not exist.")
        if not self._working_directory.is_dir():
            raise NotADirectoryError(f"Working directory {self._working_directory} is not a directory.")

        self._rdf_directory = pathlib.Path(working_directory) / "rdf"
        self._rdf_directory.mkdir(parents=True, exist_ok=True)

        self._hdf_directory = pathlib.Path(working_directory) / "hdf"
        self._hdf_directory.mkdir(parents=True, exist_ok=True)

        # write catalog to rdf directory
        catalog_path = self._rdf_directory / "catalog.ttl"
        with open(catalog_path, "w", encoding="utf-8") as f:
            f.write(self._catalog.serialize(format="ttl"))
        logger.debug(f"Wrote catalog to {catalog_path.resolve()}")

        stores = {"main_rdf_store": rdf_store}
        if add_wikidata_store:
            wikidata_store = RemoteSparqlStore(endpoint_url="https://query.wikidata.org/sparql", return_format="json")
            stores["wikidata"] = wikidata_store

        if hdf_store is None:
            hdf_store = HDF5SqlDB(data_dir=self._hdf_directory, db_path=self._hdf_directory)

        if hdf_store is not None:
            stores["hdf_store"] = hdf_store

        self._store_manager = StoreManager()
        for store_name, store in stores.items():
            if not isinstance(store, Store):
                raise TypeError(f"Expected Store, got {type(store)}")
            logger.debug(f"Adding store {store_name} to the database.")
            self.stores.add_store(store_name, store)

        logger.debug("Downloading catalog datasets...")
        filenames = _download_catalog_datasets(self._catalog, self._rdf_directory)
        logger.info(f"Catalog datasets downloaded {len(filenames)} files.")

        # populate graph if graph is empty but filenames are available
        rdf_store = self.stores["main_rdf_store"]
        if isinstance(rdf_store, RDFStore):
            if len(rdf_store.graph) == 0 and len(filenames) > 0:
                logger.debug("Populating main RDF store with downloaded datasets...")
                for filename in filenames:
                    rdf_store.upload_file(filename)
                logger.info(f"Main RDF store populated with {len(filenames)} files.")

        if augment_wikidata_knowledge and not "wikidata" in stores:
            warnings.warn("Wikidata knowledge addition requested, but no Wikidata store found.")
        if "wikidata" in stores and augment_wikidata_knowledge:
            from .query_templates import get_wikidata_property_query, get_all_wikidata_entities
            # find all wikidata entities
            res = get_all_wikidata_entities.execute(rdf_store)
            logger.debug("Adding Wikidata knowledge to the main RDF store...")

            wikidata_store = stores["wikidata"]
            for entity in res.data["wikidata_entity"]:
                sparql_query = get_wikidata_property_query(wikidata_entity=entity)
                wikidata_results = sparql_query.execute(wikidata_store)
                df = wikidata_results.data
                subj = rdflib.URIRef(entity)
                for _, row in df.iterrows():
                    pred = rdflib.URIRef(row["property"])
                    obj_value = row["value"]
                    if isinstance(obj_value, str):
                        if obj_value.startswith("http://") or obj_value.startswith("https://"):
                            obj = rdflib.URIRef(obj_value)
                        else:
                            obj = rdflib.Literal(obj_value)
                    else:
                        obj = rdflib.Literal(obj_value)
                    rdf_store.graph.add((subj, pred, obj))
            logger.info("Wikidata knowledge added to the main RDF store.")


    def __repr__(self):
        return f"{self.__class__.__name__}(stores={self.stores})"

    @property
    def catalog(self) -> dcat.Catalog:
        return self._catalog

    @property
    def working_directory(self) -> pathlib.Path:
        return self._working_directory

    @property
    def rdf_directory(self) -> pathlib.Path:
        return self._rdf_directory

    @property
    def hdf_directory(self) -> pathlib.Path:
        return self._hdf_directory

    @property
    def stores(self) -> StoreManager:
        """Returns the store manager."""
        return self._store_manager

    @property
    def rdf_stores(self) -> RDFStore:
        return {k: v for k, v in self.stores.stores.items() if isinstance(v, RDFStore)}

    @property
    def rdf_store(self) -> RDFStore:
        return self.stores["main_rdf_store"]

    @property
    def hdf_store(self) -> DataStore:
        return self.stores["hdf_store"]

    @classmethod
    def validate_config(cls, config_filename: Union[str, pathlib.Path]) -> bool:
        import pyshacl
        config_graph = rdflib.Graph()
        config_graph.parse(source=config_filename, format="ttl")
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(data=MINIMUM_DATASET_SHACL, format="ttl")
        results = pyshacl.validate(
            data_graph=config_graph,
            shacl_graph=shacl_graph,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            advanced=True,
        )
        conforms, results_graph, results_text = results
        if not conforms:
            warnings.warn("Configuration file does not conform to SHACL shapes.")
            print(" > SHACL validation results:")
            print(f" > {results_text}")
        return results

    @classmethod
    def initialize(
            cls,
            config_filename: Union[str, pathlib.Path],
            working_directory: Union[str, pathlib.Path] = None
    ) -> List[DownloadStatus]:
        if working_directory is None:
            working_directory = pathlib.Path.cwd()
        download_directory = pathlib.Path(working_directory) / "metadata"
        download_directory.mkdir(parents=True, exist_ok=True)
        print(
            f"Copying the config file {config_filename} to the target directory {download_directory.resolve()} ..."
        )
        conforms, results_graph, results_text = cls.validate_config(config_filename)
        if not conforms:
            raise ValueError(f"The provided config file is not valid according to SHACL shapes: {results_text}")

        shutil.copy(
            config_filename,
            download_directory / pathlib.Path(config_filename).name
        )
        return database_initialization(
            config_filename=config_filename,
            download_directory=download_directory
        )


__all__ = (
    "Catalog",
    "RemoteSparqlStore",
    "GraphDB",
    "InMemoryRDFStore",
    "QueryResult",
    "MetadataStore",
    "DataStore",
    "RDFStore",
    "SparqlQuery",
    "Store",
    "StoreManager",
    "HDF5SqlDB",
    "Query",
    "RemoteSparqlQuery",
    "FederatedQueryResult",
)
