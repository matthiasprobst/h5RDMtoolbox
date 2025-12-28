import json
import logging
import pathlib
import shutil
import sqlite3
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, Union, Any, List, Tuple
from typing import Optional

import pandas as pd
import rdflib
import requests
from ontolutils.ex import dcat
from rdflib import Graph

from h5rdmtoolbox.catalog.abstracts import RDFStore
from .abstracts import DataStore, Store, MetadataStore
from .utils import sparql_json_to_dataframe, sparql_result_to_df

# from ..stores import RemoteSparqlStore

logger = logging.getLogger('h5rdmtoolbox.catalog')


@dataclass
class DatabaseResource:
    identifier: Any
    metadata: rdflib.Graph

    def serialize(self, format, **kwargs) -> str:
        return self.metadata.serialize(format=format, **kwargs)


class StoreManager:
    """Store manager that manages the interaction between stores."""

    def __init__(self, stores: Dict[str, Store] = None):
        self._stores: Dict[str, DataStore] = stores if stores is not None else {}

    def __getattr__(self, item) -> Store:
        """Allows access to stores as attributes."""
        if item in self.stores:
            return self.stores[item]
        return super().__getattribute__(item)

    def __getitem__(self, item):
        """Allows access to stores via indexing."""
        return self.stores[item]

    def __len__(self):
        """Returns the number of stores managed."""
        return len(self.stores)

    def __repr__(self):
        """String representation of the DataStoreManager."""
        store_names = ", ".join(self.stores.keys())
        return f"{self.__class__.__name__}(stores=[{store_names}])"

    def __contains__(self, item) -> bool:
        """Checks if a store exists in the manager."""
        return item in self.stores

    @property
    def stores(self) -> Dict[str, Store]:
        """Returns the stores managed by the manager."""
        return self._stores

    @property
    def data_stores(self) -> Dict[str, DataStore]:
        """Alias for stores property."""
        return {k: v for k, v in self.stores.items() if isinstance(v, DataStore)}

    @property
    def metadata_stores(self) -> Dict[str, MetadataStore]:
        """Alias for stores property."""
        return {k: v for k, v in self.stores.items() if isinstance(v, MetadataStore)}

    def add_store(self, store_name: str, store: Store):
        """Add a new store to the manager."""
        if store_name in self.stores:
            raise ValueError(f"DataStore with name {store_name} already exists.")
        self.stores[store_name] = store


# concrete implementations of Store


class RemoteSparqlStore(MetadataStore):

    def __init__(self, endpoint_url, return_format: str = None):
        try:
            from SPARQLWrapper import SPARQLWrapper
        except ImportError:
            raise ImportError("Please install SPARQLWrapper to use this class: 'pip install SPARQLWrapper'")

        self._wrapper = SPARQLWrapper(endpoint_url)
        if return_format is not None:
            self._wrapper.setReturnFormat(return_format)

    @property
    def wrapper(self):
        return self._wrapper

    def _upload_file(self, filename: Union[str, pathlib.Path], validate: bool = True,
                    skip_unsupported: bool = False) -> bool:
        """Uploads a file to the remote SPARQL endpoint."""
        raise NotImplementedError("Remote SPARQL Store does not support file uploads.")


class GraphDB(RemoteSparqlStore):
    """GraphDB RDF database store."""
    __supported_file_extensions__ = {".ttl", ".rdf", ".jsonld"}

    def __init__(self,
                 endpoint: str,
                 repository: str,
                 username: str = None,
                 password: str = None):
        super().__init__(f"{endpoint}/repositories/{repository}")
        try:
            from SPARQLWrapper import SPARQLWrapper, JSON
        except ImportError:
            raise ImportError("Please install SPARQLWrapper to use this class: pip install SPARQLWrapper")
        self._endpoint = endpoint
        self._repository = repository
        self._username = username
        self._password = password
        self._wrapper.setReturnFormat(JSON)
        if self.username and self.password:
            self._wrapper.setCredentials(self.username, self.password)

        repo_info = self.get_repository_info(self.repository)
        if not repo_info:
            logger.info(f"The repository '{self.repository}' does not exist. "
                        "Call create_repository('config.ttl') with a valid configuration "
                        "('config.ttl') file to create it.")

    def __repr__(self):
        return f"<{self.__class__.__name__} (GraphDB-Repo={self.get_repository_info()['id']})>"

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def repository(self) -> str:
        return self._repository

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    def _upload_file(self, filename: Union[str, pathlib.Path], validate: bool = True,
                    skip_unsupported: bool = False) -> bool:
        """Uploads an RDF file to das GraphDB-Repository."""
        filename = pathlib.Path(filename).resolve().absolute()
        if filename.suffix not in self.__supported_file_extensions__:
            if not skip_unsupported:
                raise ValueError(f"File type {filename.suffix} not supported.")
            if skip_unsupported:
                return False
        if not filename.exists():
            raise FileNotFoundError(f"File {filename} not found.")
        # Determine content type based on file extension
        ext = filename.suffix.lower()
        if ext == ".ttl":
            content_type = "text/turtle"
        elif ext == ".rdf":
            content_type = "application/rdf+xml"
        elif ext == ".jsonld":
            content_type = "application/ld+json"
        else:
            raise ValueError(f"File form '{ext}' not supported.")
        # Target URL
        url = f"{self.endpoint}/repositories/{self.repository}/statements"
        with open(filename, "rb") as f:
            data = f.read()
        headers = {"Content-Type": content_type}
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.post(url, data=data, headers=headers, auth=auth)
        if response.status_code in (200, 201, 204):
            return True
        else:
            raise RuntimeError(f"Upload failed: {response.status_code} {response.text}")

    def create_repository(self, config_path: Union[str, pathlib.Path]) -> bool:
        """Creates a GraphDB repository using a configuration file (repo-config.ttl)."""
        config_path = pathlib.Path(config_path).resolve().absolute()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}.")
        url = f"{self.endpoint}/rest/repositories"
        auth = (self.username, self.password) if self.username and self.password else None
        with open(config_path, "rb") as f:
            files = {"config": (config_path.name, f, "application/x-turtle")}
            response = requests.post(url, files=files, auth=auth)
        if response.status_code in (201, 204):
            return True
        else:
            raise RuntimeError(f"Repository konnte nicht angelegt werden: {response.status_code} {response.text}")

    def list_repositories(self) -> Any:
        """Lists all repositories in the GraphDB instance."""
        url = f"{self.endpoint}/rest/repositories"
        headers = {"Accept": "application/json"}
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.get(url, headers=headers, auth=auth)
        if response.status_code == 200:
            return response.json()
        return None

    def get_repository_info(self, repository=None) -> Dict:
        """Returns information about a specific repository."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}"
        headers = {"Accept": "application/json"}
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.get(url, headers=headers, auth=auth)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            logger.debug(f"Repository '{repo}' does not exist.")
            return {}
        if response.status_code == 401:
            raise RuntimeError(f"Unauthorized access to repository '{repo}'. Check your credentials.")
        if response.status_code == 403:
            raise RuntimeError(f"Forbidden access to repository '{repo}'. Check your permissions.")
        raise RuntimeError(f"Error fetching repository info: {response.status_code} {response.text}")

    def get_or_create_repository(self, config_path: Union[str, pathlib.Path]) -> bool:
        """Gets the repository info if it exists, otherwise creates it using the provided config file."""
        if self.get_repository_info(self.repository):
            logger.debug(f"Found existing repository '{self.repository}'.")
            return True
        logger.debug(f"Repository '{self.repository}' does not exist. Creating it.")
        return self.create_repository(config_path)

    def count_triples(self, key: str = "total", repository: str = None) -> int:
        """Counts the number of triples in a repository.

        Parameters
        ----------
        key : str, optional
            The key to extract the count from the response. Default is "total". Other options are
            "explicit", "inferred".
        repository : str, optional
            The name of the repository to count triples in. If None, uses the default repository.
        """
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}/size"
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            try:
                data = response.json()
                return int(data.get(key, 0))
            except Exception:
                raise RuntimeError(f"Error parsing the triple number: {response.text}")
        else:
            raise RuntimeError(f"Error fetching the triple number: {response.status_code} {response.text}")

    def restart_repository(self, repository: str = None) -> bool:
        """Restarts a repository in the GraphDB instance."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}/restart"
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.post(url, auth=auth)
        if response.status_code in (200, 204):
            return True
        else:
            raise RuntimeError(f"Error restarting the repository: {response.status_code} {response.text}")

    def delete_repository(self, repository: str = None) -> bool:
        """Deletes a repository from the GraphDB instance."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}"
        auth = (self.username, self.password) if self.username and self.password else None
        response = requests.delete(url, auth=auth)
        if response.status_code in (200, 204):
            return True
        else:
            raise RuntimeError(f"Error deleting the repository: {response.status_code} {response.text}")


class InMemoryRDFStore(RDFStore):
    """In-memory RDF database that can upload files and return a combined graph."""

    __default_expected_file_extensions__ = {".ttl", ".rdf", ".jsonld", ".nt", ".xml", ".n3"}
    __populate_on_init__ = True

    def __init__(
            self,
            data_dir: Union[str, pathlib.Path],
            recursive_exploration: bool = True,
            formats: Union[str, List[str], Tuple[str]] = None
    ):
        """Initializes the InMemoryRDFStore.

        Parameters
        ----------
        data_dir : Union[str, pathlib.Path]
            The directory where RDF files are stored.
        recursive_exploration : bool, optional
            If True, the directory will be explored recursively for RDF files. Default is False.
        formats : Union[str, List[str], Tuple[str]], optional
            The expected file formats/extensions. Can be a single string or a list/tuple of strings.
            Default is None, which uses the default expected file extensions.
        """
        if formats is None:
            formats = self.__default_expected_file_extensions__
        elif isinstance(formats, str):
            formats = {f".{formats.lstrip('.')}", }
        elif isinstance(formats, (list, set, tuple)):
            formats = {f".{fmt.lstrip('.')}" for fmt in formats}
        else:
            raise ValueError("formats must be a string or a list/set/tuple of strings.")

        for _fmt in formats:
            if _fmt not in self.__default_expected_file_extensions__:
                raise ValueError(f"File format '{_fmt}' not supported.")

        self._expected_file_extensions = formats
        self._data_dir = pathlib.Path(data_dir).resolve()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._recursive_exploration = recursive_exploration
        self._filenames = []
        self._graphs = {}
        self._combined_graph = rdflib.Graph()
        if self.__populate_on_init__:
            self.populate()

    @property
    def data_dir(self) -> pathlib.Path:
        """Returns the data directory where files are stored."""
        return self._data_dir
    def populate(self, recursive: bool = None) -> "InMemoryRDFStore":
        """Populates the RDF store by scanning the data directory for RDF files and adding them to the graph."""
        _recursive_exploration = recursive or self._recursive_exploration
        for _ext in self._expected_file_extensions:
            if _recursive_exploration:
                self._filenames.extend([f.resolve().absolute() for f in self.data_dir.rglob(f"*{_ext}")])
            else:
                self._filenames.extend([f.resolve().absolute() for f in self.data_dir.glob(f"*{_ext}")])
        self._filenames = list(set(self._filenames))  # remove duplicates
        for filename in self._filenames:
            logger.debug(f"Adding file '{filename}' to the RDF store {self.__class__.__name__}.")
            self._add_to_graph(filename)
        return self

    @property
    def filenames(self):
        """Returns the list of filenames uploaded to the store."""
        return self._filenames

    def _upload_file(
            self,
            filename: Union[str, pathlib.Path],
            validate: bool = True,
            skip_unsupported: bool = False) -> bool:
        """Uploads a file to the in-memory RDF store.

        Parameters
        ----------
        filename : Union[str, pathlib.Path]
            The path to the RDF file to upload.
        validate : bool, optional
            If True, the file will be validated before uploading. Default is True.
        skip_unsupported : bool, optional
            If True, unsupported file types will be skipped without raising an error.

        Returns
        -------
        bool
            True if the file was uploaded successfully, False if skipped due to unsupported type.
        """
        filename = pathlib.Path(filename).resolve().absolute()
        if not filename.exists():
            raise FileNotFoundError(f"File {filename} not found.")
        if filename.suffix not in self._expected_file_extensions:
            if not skip_unsupported:
                raise ValueError(f"File type {filename.suffix} not supported.")
            if skip_unsupported:
                return False
        if filename in self._filenames:
            self._filenames.remove(filename)
        self._filenames.append(filename)
        if filename.parent != self.data_dir:
            shutil.copy(filename, self.data_dir / filename.name)
        self._add_to_graph(filename)
        return True

    def _add_to_graph(self, filename: pathlib.Path):
        """Adds the RDF graph from the file to the combined graph."""
        g = self._graphs.get(filename, None)
        if not g:
            g = rdflib.Graph()
            try:
                g.parse(filename)
            except Exception as e:
                raise ValueError(f"Could not parse file '{filename}'. Error: {e}")
            for s, p, o in g:
                if isinstance(s, rdflib.BNode):
                    new_s = rdflib.URIRef(f"https://example.org/{s}")
                else:
                    new_s = s
                if isinstance(o, rdflib.BNode):
                    new_o = rdflib.URIRef(f"https://example.org/{o}")
                else:
                    new_o = o
                g.remove((s, p, o))
                g.add((new_s, p, new_o))
            self._graphs[filename] = g
            self._combined_graph += g

    @property
    def graph(self) -> rdflib.Graph:
        return self._combined_graph

    def reset(self, *args, **kwargs):
        self._filenames = []
        self._graphs = rdflib.Graph()
        self._combined_graph = rdflib.Graph()
        return self


class AbstractQuery(ABC):

    @abstractmethod
    def execute(self, store: "Store") -> "QueryResult":
        """Executes the query."""


class QueryResult:

    def __init__(self,
                 query: AbstractQuery,
                 data: Any,
                 bindings: Any = None,
                 description: Optional[str] = None,
                 derived_graph: Optional[Graph] = None):
        self.query = query
        self.data = data
        self.bindings = bindings
        self.description = description
        self.derived_graph = derived_graph

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"{self.__class__.__name__}(\n  query={self.query},\n  data={self.data},\n  description={self.description}\n)"


@dataclass(frozen=True)
class FederatedQueryResult:
    data: Any
    metadata: Dict


class Query(AbstractQuery, ABC):

    def __init__(self, query, description=None):
        self.query = query
        self.description = description

    def __eq__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.query == other.query and self.description == other.description

    def __repr__(self):
        description_repr = self.description or ""
        return f"{self.__class__.__name__}(query=\"{self.query}\", description=\"{description_repr}\")"


class DataStoreQuery(Query, ABC):
    """Data store query interface (concrete implementations can be sql or non sql query)."""


class SQLQuery(DataStoreQuery):

    def __init__(self, query: str, description: str = None, filters=None, ):
        super().__init__(query, description)
        self.filters = filters

    def execute(self, *args, **kwargs) -> QueryResult:
        pass


class HDF5SqlDB(DataStore):
    """
    HDF5SQLDB is a SQL database interface that stores data in HDF5 files.
    """

    def __init__(self, data_dir: Union[str, pathlib.Path], db_path: Union[str, pathlib.Path] = None):
        if data_dir is not None and db_path is not None:
            raise ValueError("Specify either data_dir or db_path, not both.")
        if db_path is not None:
            db_path = pathlib.Path(db_path).resolve().absolute()
            if not db_path.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
                db_path.touch()
            if not db_path.is_file():
                raise ValueError(f"Database path {db_path} is not a file.")
        else:
            data_dir = pathlib.Path(data_dir).resolve().absolute()
            assert data_dir.exists(), f"Data directory {data_dir} does not exist."
            assert data_dir.is_dir(), f"Data directory {data_dir} is not a directory."
            db_path = data_dir / "hdf5_files.db"

        self._hdf5_file_table_name = "hdf5_files"
        self._sql_base_uri = "http://local.org/sqlite3/"
        self._db_path = db_path
        self._endpointURL = rf"file://{self._db_path}"
        self._connection = self._initialize_database(self._db_path)
        self._filenames = {}
        self._expected_file_extensions = {".hdf", ".hdf5", ".h5"}

    def __repr__(self):
        return f"<{self.__class__.__name__} (Endpoint URL={self._endpointURL})>"

    def _upload_file(self, filename, validate: bool = True, skip_unsupported: bool = False) -> DatabaseResource:
        _id = self._insert_hdf5_reference(self._connection, filename)
        return DatabaseResource(_id, metadata=self.generate_mapping_dataset(str(_id)))

    def execute_query(self, query: SQLQuery) -> QueryResult:
        cursor = self._connection.cursor()
        params = []

        if query.filters:
            for key, value in query.filters.items():
                query += f" AND {key} = ?"
                params.append(value)

        cursor.execute(query.sql_query, params)
        return cursor.fetchall()

    def _initialize_database(self, db_path: Union[str, pathlib.Path] = "hdf5_files.db"):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {self._hdf5_file_table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """)
        conn.commit()
        return conn

    def reset(self):
        logger.info(f"Resetting the database. Dropping table {self._hdf5_file_table_name}.")
        cursor = self._connection.cursor()
        cursor.execute(f"DROP TABLE {self._hdf5_file_table_name}")
        self._initialize_database(self._db_path)

    @classmethod
    def _insert_hdf5_reference(cls, conn, filename, metadata=None):
        filename = pathlib.Path(filename).resolve().absolute()
        cursor = conn.cursor()
        metadata_dump = json.dumps(metadata) or '{}'
        try:
            cursor.execute("""
            INSERT INTO hdf5_files (file_path, metadata)
            VALUES (?, ?)
            """, (str(filename), metadata_dump))
            conn.commit()
            generated_id = cursor.lastrowid
            logger.debug(f"File {filename} inserted successfully.")
            return generated_id
        except sqlite3.IntegrityError:
            logger.error(f"File {filename} already exists.")

    def __del__(self):
        """Ensure the connection is closed when the object is deleted."""
        if self._connection:
            self._connection.close()

    def generate_data_service_serving_a_dataset(self, dataset_identifier: str):
        endpoint_url = self._endpointURL
        endpoint_url_file_name = endpoint_url.rsplit('/', 1)[-1]
        dataservice_id = f"{self._sql_base_uri}{endpoint_url_file_name}"
        data_service = dcat.DataService(
            id=dataservice_id,
            title="sqlite3 Database",
            endpointURL=endpoint_url,
            servesDataset=dcat.Dataset(
                id=f"{self._sql_base_uri}table/{self._hdf5_file_table_name}",
                title=f"SQL Table '{self._hdf5_file_table_name}'",
                identifier=self._hdf5_file_table_name,
                distribution=dcat.Distribution(
                    id=f"{self._sql_base_uri}12345",
                    identifier=dataset_identifier,
                    mediaType="application/vnd.sqlite3",
                )
            )
        )
        return data_service

    def generate_mapping_dataset(self, dataset_identifier: str):
        data_service = self.generate_data_service_serving_a_dataset(dataset_identifier)
        return rdflib.Graph().parse(data=data_service.model_dump_jsonld(), format="json-ld")


class MetadataStoreQuery(Query, ABC):
    """RDF Store Query interface."""


class SparqlQuery(MetadataStoreQuery):
    """A SPARQL query interface for RDF stores."""

    def execute(self, store: RDFStore, *args, **kwargs) -> QueryResult:
        """Execute the SPARQL query against the given RDF store.

        Parameters
        ----------
        store : RDFStore
            The RDF store to execute the query against.
        *args
            Additional positional arguments to pass to the store's query method.
        **kwargs
            Additional keyword arguments to pass to the store's query method.

        Returns
        -------
        QueryResult
            The result of the query execution.
        """
        if isinstance(store, RemoteSparqlStore):
            return RemoteSparqlQuery(self.query, self.description).execute(store)
        res = store.graph.query(self.query, *args, **kwargs)
        bindings = res.bindings
        try:
            derived_graph = res.graph
        except AttributeError:
            derived_graph = None
        if bindings is None:
            return QueryResult(
                query=self,
                data=pd.DataFrame(),
                bindings=bindings,
                description=self.description,
                derived_graph=derived_graph
            )
        return QueryResult(
            query=self,
            data=sparql_result_to_df(bindings),
            bindings=bindings,
            description=self.description,
            derived_graph=derived_graph
        )


class RemoteSparqlQuery(MetadataStoreQuery):

    def execute(self, store: RemoteSparqlStore, *args, **kwargs) -> QueryResult:
        if not isinstance(store, RemoteSparqlStore):
            raise TypeError("store must be an instance of RemoteSparqlStore.")
        sparql = store.wrapper
        sparql.setQuery(self.query)

        results = sparql.queryAndConvert()

        try:
            data = sparql_json_to_dataframe(results)
        except Exception as e:
            logger.debug("Failed to convert SPARQL results to DataFrame: %s", e)
            data = results
        return QueryResult(
            query=self,
            data=data,
            description=self.description
        )
