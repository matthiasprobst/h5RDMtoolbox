import logging
import pathlib
import shutil
import warnings
from typing import Dict
from typing import Union, List

import rdflib

from ._initialization import database_initialization, DownloadStatus
from .core import MetadataStore, DataStore, RDFStore, Store, RemoteSparqlStore, StoreManager, HDF5SqlDB, Query, \
    RemoteSparqlQuery, QueryResult, SparqlQuery, GraphDB, InMemoryRDFStore
from .profiles import MINIMUM_DATASET_SHACL

logger = logging.getLogger("h5rdmtoolbox.catalog")


class Catalog:
    """Catalog class to manage multiple metadata and data stores."""

    def __init__(
            self,
            metadata_stores: Dict[str, MetadataStore],
            hdf_store: DataStore = None,
            add_wikidata_store: bool = False
    ):
        if add_wikidata_store:
            if "wikidata" in metadata_stores:
                raise ValueError("Wikidata store (at least the name) is already present in metadata_stores.")
            wikidata_store = RemoteSparqlStore(endpoint_url="https://query.wikidata.org/sparql", return_format="json")
            metadata_stores["wikidata"] = wikidata_store
        stores = metadata_stores

        if hdf_store is None:
            hdf_store = HDF5SqlDB(data_dir=self.working_dir)

        if hdf_store is not None:
            stores["hdf_store"] = hdf_store

        self._store_manager = StoreManager()
        for store_name, store in stores.items():
            if not isinstance(store, Store):
                raise TypeError(f"Expected Store, got {type(store)}")
            logger.debug(f"Adding store {store_name} to the database.")
            self.stores.add_store(store_name, store)

    def __repr__(self):
        return f"{self.__class__.__name__}(stores={self.stores})"

    @property
    def stores(self) -> StoreManager:
        """Returns the store manager."""
        return self._store_manager

    @property
    def metadata_stores(self) -> StoreManager:
        return StoreManager(
            self.stores.metadata_stores
        )

    @property
    def rdf_stores(self) -> RDFStore:
        return {k: v for k, v in self.stores.stores.items() if isinstance(v, RDFStore)}

    @property
    def hdf_store(self) -> DataStore:
        return self.stores.hdf_store

    @property
    def data_stores(self) -> StoreManager:
        """Alias for stores property."""
        return StoreManager(
            self.stores.data_stores
        )

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
)
