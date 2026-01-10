import logging
import pathlib
import shutil
import warnings
from typing import Union, List, Dict, Optional

import pandas as pd
import pyshacl
import rdflib
from ontolutils.ex import dcat, prov

from ._initialization import database_initialization, DownloadStatus
from .core import (
    MetadataStore,
    DataStore,
    RDFStore,
    Store,
    RemoteSparqlStore,
    StoreManager,
    HDF5SqlDB,
    Query,
    RemoteSparqlQuery,
    QueryResult,
    SparqlQuery,
    GraphDB,
    InMemoryRDFStore,
    FederatedQueryResult,
    MetadataStoreQuery,
)
from .stores.hdf5 import HDF5FileStore
from .profiles import IS_VALID_CATALOG_SHACL
from .query_templates import GET_ALL_METADATA_CATALOG_DATASETS
from .stores.hdf5 import HDF5Store
from .utils import WebResource, download
from ..repository.zenodo import ZenodoRecord

logger = logging.getLogger("h5rdmtoolbox.catalog")


def _parse_catalog(
        catalog: Union[str, pathlib.Path, ZenodoRecord, dcat.Catalog],
) -> dcat.Catalog:
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
        raise NotImplementedError(
            "Loading catalog from ZenodoRecord is not implemented yet."
        )
    if isinstance(catalog, (str, pathlib.Path)):
        catalog_path = pathlib.Path(catalog)
        if not catalog_path.exists():
            raise FileNotFoundError(f"Catalog file {catalog} does not exist.")
        catalogs = dcat.Catalog.from_ttl(source=catalog)
        if len(catalogs) > 1:
            raise ValueError(
                f"Multiple catalogs found in file {catalog}. Expected only one."
            )
        if len(catalogs) == 0:
            raise ValueError(f"No catalog found in file {catalog}.")
        return catalogs[0]
    raise TypeError(f"Unsupported catalog type: {type(catalog)}")


def _validate_catalog(catalog: dcat.Catalog) -> bool:
    """Validates the catalog against the SHACL shapes."""
    catalog_graph = rdflib.Graph()
    catalog_graph.parse(data=catalog.serialize("ttl"), format="ttl")
    shacl_graph = rdflib.Graph()
    shacl_graph.parse(data=IS_VALID_CATALOG_SHACL, format="ttl")
    results = pyshacl.validate(
        data_graph=catalog_graph,
        shacl_graph=shacl_graph,
        inference="rdfs",
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


def _download_catalog_datasets(
        catalog: dcat.Catalog, download_directory: pathlib.Path
) -> List[DownloadStatus]:
    """Downloads all datasets in the catalog to the specified directory."""
    g = rdflib.Graph()
    g.parse(data=catalog.serialize("ttl"), format="ttl")

    results = g.query(GET_ALL_METADATA_CATALOG_DATASETS.query)

    logger.debug("found datasets:", len(results))
    list_of_ttl_web_resources = [
        WebResource(
            download_url=row.download,
            checksum=row.checksumValue,
            title=row.title,
            identifier=row.identifier,
            mediaType="text/turtle",
        )
        for row in results
    ]

    n_ttl_resources = len(list_of_ttl_web_resources)
    logger.debug(
        f"Found {n_ttl_resources} TTL web resources to download. Downloading to {download_directory}..."
    )
    return download(
        download_directory=download_directory, web_resources=list_of_ttl_web_resources
    )


def _query_catalog_from_rdf_store(rdf_store: RDFStore) -> dcat.Catalog:
    """Queries the catalog from the given RDF store."""
    q = dcat.Catalog.create_query()
    res = rdf_store.graph.query(q)
    cat = dcat.Catalog.from_sparql(res)

    if len(cat) != 1:
        raise ValueError(f"Expected one catalog in RDF store, found {len(cat)}.")

    _creators = []
    creator = cat[0].creator
    if creator is not None:
        if isinstance(creator, str):
            _creator = prov.Person.from_graph(rdf_store.graph, subject=creator)
            _creators.extend(_creator)
        elif isinstance(creator, list):
            for person in creator:
                if isinstance(person, str):
                    _creator = prov.Person.from_graph(rdf_store.graph, subject=person)
                    _creators.extend(_creator)
    if len(_creators) > 0:
        if len(_creators) == 1:
            cat[0].creator = _creators[0]
        else:
            cat[0].creator = _creators
    # augment catalog with datasets and distributions
    _datasets = []
    if cat[0].dataset is None:
        return cat[0]

    for dataset_iri in cat[0].dataset:
        datasets = dcat.Dataset.from_graph(rdf_store.graph, subject=dataset_iri)
        _distributions = []
        for dataset in datasets:
            distributions = dataset.distribution
            if distributions is None:
                continue
            for distribution_iri in dataset.distribution:
                dist = dcat.Distribution.from_graph(
                    rdf_store.graph, subject=distribution_iri
                )
                _distributions.extend(dist)
            dataset.distribution = _distributions
        _datasets.extend(datasets)
    cat[0].dataset = _datasets
    return cat[0]


class CatalogManager:
    """Catalog managerclass to manage multiple metadata and data stores.

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
            catalog: Optional[Union[str, pathlib.Path, ZenodoRecord, dcat.Catalog]] = None,
            working_directory: Union[str, pathlib.Path] = None,
    ):
        """Initializes the Catalog.

        Parameters:
            rdf_store (MetadataStore): The main RDF metadata store.
            hdf_store (DataStore, optional): The HDF5 data store. If None
                a default HDF5SqlDB store will be created.
            working_directory (Union[str, pathlib.Path], optional): The
                working directory for the catalog. If None, uses the current
                working directory. Defaults to None.
            secondary_rdf_stores: (Dict[str, RDFStore], optional): Additional RDF stores
                to add to the catalog's store manager. Defaults to None.
        """
        if catalog is not None:
            self._catalog = _parse_catalog(catalog)
        else:
            self._catalog = None

        self._rdf_directory, self._hdf_directory = self._setup_file_structure(
            working_directory
        )
        self._store_manager = StoreManager()

        if catalog is not None:
            catalog_path = self._rdf_directory / "catalog.ttl"
            with open(catalog_path, "w", encoding="utf-8") as f:
                f.write(self._catalog.serialize(format="ttl"))
            logger.debug(f"Wrote catalog to {catalog_path.resolve()}")

    def add_main_rdf_store(self, rdf_store: MetadataStore):
        """Adds the main RDF store to the catalog's store manager."""
        if not isinstance(rdf_store, MetadataStore):
            raise TypeError(f"Expected MetadataStore, got {type(rdf_store)}")
        if "main_rdf_store" in self.stores:
            raise KeyError(
                "Main RDF store already exists in the catalog. Use 'add_rdf_store()' to add additional stores."
            )
        self.stores.add_store("main_rdf_store", rdf_store)

    def add_hdf_store(self, hdf_store: DataStore):
        """Adds the HDF5 data store to the catalog's store manager."""
        if not isinstance(hdf_store, DataStore):
            raise TypeError(f"Expected DataStore, got {type(hdf_store)}")
        self.stores.add_store("hdf_store", hdf_store)

    def add_secondary_rdf_store(self, store_name: str, rdf_store: MetadataStore):
        """Adds a secondary RDF store to the catalog's store manager."""
        if not isinstance(rdf_store, MetadataStore):
            raise TypeError(f"Expected MetadataStore, got {type(rdf_store)}")
        self.stores.add_store(store_name, rdf_store)

    def download_metadata(self):
        logger.debug("Downloading catalog datasets...")
        download_stati = _download_catalog_datasets(self.catalog, self.rdf_directory)
        logger.info(f"Catalog datasets downloaded {len(download_stati)} files.")

        rdf_store = self.main_rdf_store
        if isinstance(rdf_store, RDFStore):
            if len(rdf_store.graph) == 0 and len(download_stati) > 0:
                logger.debug("Populating main RDF store with downloaded datasets...")
                for download_status in download_stati:
                    rdf_store.upload_file(
                        download_status.filename, skip_unsupported=True
                    )
                logger.info(
                    f"Main RDF store populated with {len(download_stati)} files."
                )

    @staticmethod
    def _setup_file_structure(
            working_directory: Union[str, pathlib.Path],
            rdf_directory: Union[str, pathlib.Path] = None,
    ):
        if working_directory is None:
            working_directory = pathlib.Path.cwd()
        _working_directory = pathlib.Path(working_directory)
        if not _working_directory.exists():
            raise NotADirectoryError(
                f"Working directory {_working_directory} does not exist."
            )
        if not _working_directory.is_dir():
            raise NotADirectoryError(
                f"Working directory {_working_directory} is not a directory."
            )

        if rdf_directory is None:
            _rdf_directory = pathlib.Path(working_directory) / "rdf"
        else:
            _rdf_directory = pathlib.Path(rdf_directory)
        _rdf_directory.mkdir(parents=True, exist_ok=True)

        _hdf_directory = pathlib.Path(working_directory) / "hdf"
        _hdf_directory.mkdir(parents=True, exist_ok=True)

        return _rdf_directory, _hdf_directory

    def __repr__(self):
        return f"{self.__class__.__name__}(stores={self.stores})"

    @property
    def catalog(self) -> dcat.Catalog:
        if self._catalog is None:
            self._catalog = _query_catalog_from_rdf_store(self.main_rdf_store)
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
    def rdf_stores(self) -> Dict[str, RDFStore]:
        return {k: v for k, v in self.stores.stores.items() if isinstance(v, RDFStore)}

    @property
    def main_rdf_store(self) -> RDFStore:
        """Returns the main RDF store."""
        if "main_rdf_store" not in self.stores:
            raise KeyError(
                "No main RDF store found in the catalog. Please add one using 'add_main_rdf_store()'."
            )
        return self.stores["main_rdf_store"]

    @property
    def hdf_store(self) -> DataStore:
        return self.stores["hdf_store"]

    @classmethod
    def validate_catalog(cls, catalog_filename: Union[str, pathlib.Path]) -> bool:
        import pyshacl

        config_graph = rdflib.Graph()
        config_graph.parse(source=catalog_filename, format="ttl")
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(data=IS_VALID_CATALOG_SHACL, format="ttl")
        results = pyshacl.validate(
            data_graph=config_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
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
            working_directory: Union[str, pathlib.Path] = None,
    ) -> List[DownloadStatus]:
        if working_directory is None:
            working_directory = pathlib.Path.cwd()
        download_directory = pathlib.Path(working_directory) / "metadata"
        download_directory.mkdir(parents=True, exist_ok=True)
        print(
            f"Copying the config file {config_filename} to the target directory {download_directory.resolve()} ..."
        )
        conforms, results_graph, results_text = cls.validate_catalog(config_filename)
        if not conforms:
            raise ValueError(
                f"The provided config file is not valid according to SHACL shapes: {results_text}"
            )

        shutil.copy(
            config_filename, download_directory / pathlib.Path(config_filename).name
        )
        return database_initialization(
            config_filename=config_filename, download_directory=download_directory
        )

    def add_rdf_store(self, store_name: str, rdf_store: RDFStore):
        """Adds an RDF store to the catalog's store manager."""
        if not isinstance(rdf_store, RDFStore):
            raise TypeError(f"Expected RDFStore, got {type(rdf_store)}")
        self.stores.add_store(store_name, rdf_store)

    def add_wikidata_store(
            self,
            store_name: str = "wikidata",
            augment_main_rdf_store: bool = False,
            exists_ok: bool = False,
    ):
        """Adds a Wikidata SPARQL store to the catalog's store manager.

        Parameters:
        -----------
        store_name (str): The name of the store to add. Default is "wikidata".
        augment_main_rdf_store (bool): If True, augments the main RDF store with
            additional knowledge from Wikidata based on existing entities.
            Default is False.
        """
        if store_name in self.stores and not exists_ok:
            raise KeyError(
                f"Store with name '{store_name}' already exists in the catalog. Use 'exists_ok=True' to overwrite."
            )
        if store_name in self.stores and exists_ok:
            wikidata_store = self.stores[store_name]
        else:
            wikidata_store = RemoteSparqlStore(
                endpoint_url="https://query.wikidata.org/sparql", return_format="json"
            )
            self.stores.add_store(store_name, wikidata_store)

        if augment_main_rdf_store:
            _count = 0
            from .query_templates import (
                get_wikidata_property_query,
                GET_ALL_WIKIDATA_ENTITIES,
            )

            main_rdf_store = self.main_rdf_store
            # find all wikidata entities
            res = GET_ALL_WIKIDATA_ENTITIES.execute(main_rdf_store)
            logger.debug("Adding Wikidata knowledge to the main RDF store...")

            if res.data.empty:
                logger.info(
                    "No Wikidata entities found in the main RDF store. Skipping Wikidata knowledge addition."
                )
                return
            for entity in res.data["wikidata_entity"]:
                sparql_query = get_wikidata_property_query(wikidata_entity=entity)
                wikidata_results = sparql_query.execute(wikidata_store)
                df = wikidata_results.data
                subj = rdflib.URIRef(entity)
                for _, row in df.iterrows():
                    pred = rdflib.URIRef(row["property"])
                    obj_value = row["value"]
                    if isinstance(obj_value, str):
                        if obj_value.startswith("http://") or obj_value.startswith(
                                "https://"
                        ):
                            obj = rdflib.URIRef(obj_value)
                        else:
                            obj = rdflib.Literal(obj_value)
                    else:
                        obj = rdflib.Literal(obj_value)
                    _count += 1
                    main_rdf_store.graph.add((subj, pred, obj))
            logger.info(f"Added {_count} wikidata triples to the main RDF store.")

    def execute_query(self, query: Query) -> QueryResult:
        """Depending on the query type, executes the query on the appropriate store(s).
        Since there are possibly multiple RDF stores, the results are combined.
        """
        if isinstance(query, MetadataStoreQuery):
            all_res = [
                query.execute(rdf_store) for rdf_store in self.rdf_stores.values()
            ]
            if len(all_res) == 1:
                return all_res[0]
            first_res = all_res[0]
            combined_data = pd.concat([r.data for r in all_res], ignore_index=True)
            res = QueryResult(data=combined_data, query=first_res.query)
            return res
        else:
            raise TypeError(f"Unsupported query type: {type(query)}")

    def upload_hdf_file(self, hdf_filename):
        from .. import serialize
        download_url = str(pathlib.Path(hdf_filename).resolve().as_uri())
        hdf_dist = dcat.Distribution(
            id=download_url, download_URL=download_url,
            mediaType="application/x-hdf5",
        )
        _filename = pathlib.Path(hdf_filename).name
        file_uri = download_url.strip(_filename)
        hdf_ttl = serialize(hdf_filename, format="ttl", file_uri=file_uri)
        self.main_rdf_store.upload_data(data=hdf_ttl, format="ttl")
        self.hdf_store.upload_file(distribution=hdf_dist)
        return hdf_dist


__all__ = (
    "CatalogManager",
    "RemoteSparqlStore",
    "GraphDB",
    "InMemoryRDFStore",
    "QueryResult",
    "MetadataStore",
    "HDF5FileStore",
    "DataStore",
    "RDFStore",
    "SparqlQuery",
    "Store",
    "StoreManager",
    "HDF5SqlDB",
    "HDF5Store",
    "Query",
    "RemoteSparqlQuery",
    "FederatedQueryResult",
)
