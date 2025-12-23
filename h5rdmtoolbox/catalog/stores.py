import logging
import pathlib
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Union, Any

import rdflib
import requests

logger = logging.getLogger('h5rdmtoolbox.catalog')


class Store(ABC):
    """Store interface."""

    # @property
    # @abstractmethod
    # def query(self) -> Type[Query]:
    #     """Returns the query class for the store."""

    @abstractmethod
    def upload_file(self, filename: Union[str, pathlib.Path]) -> Any:
        """Uploads a file to the store."""

    def __repr__(self):
        """String representation of the Store."""
        return f"{self.__class__.__name__}()"


class DataStore(Store, ABC):
    """Data store interface (concrete implementations can be sql or non sql databases)."""

    @abstractmethod
    def upload_file(self, filename: Union[str, pathlib.Path]):
        """Insert data into the data store."""


class MetadataStore(Store, ABC):
    """Metadata database interface using."""

    @abstractmethod
    def upload_file(self, filename: Union[str, pathlib.Path]) -> bool:
        """Insert data into the data store."""


class RDFStore(MetadataStore, ABC):
    namespaces = {
        "ex": "https://example.org/",
        "afn": "http://jena.apache.org/ARQ/function#",
        "agg": "http://jena.apache.org/ARQ/function/aggregate#",
        "apf": "http://jena.apache.org/ARQ/property#",
        "array": "http://www.w3.org/2005/xpath-functions/array",
        "dcat": "http://www.w3.org/ns/dcat#",
        "dcterms": "http://purl.org/dc/terms/",
        "fn": "http://www.w3.org/2005/xpath-functions",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "geoext": "http://rdf.useekm.com/ext#",
        "geof": "http://www.opengis.net/def/function/geosparql/",
        "gn": "http://www.geonames.org/ontology#",
        "graphdb": "http://www.ontotext.com/config/graphdb#",
        "list": "http://jena.apache.org/ARQ/list#",
        "local": "https://doi.org/10.5281/zenodo.14175299/",
        "m4i": "http://w3id.org/nfdi4ing/metadata4ing#",
        "map": "http://www.w3.org/2005/xpath-functions/map",
        "math": "http://www.w3.org/2005/xpath-functions/math",
        "ofn": "http://www.ontotext.com/sparql/functions/",
        "omgeo": "http://www.ontotext.com/owlim/geo#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "path": "http://www.ontotext.com/path#",
        "prov": "http://www.w3.org/ns/prov#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rep": "http://www.openrdf.org/config/repository#",
        "sail": "http://www.openrdf.org/config/sail#",
        "schema": "https://schema.org/",
        "spif": "http://spinrdf.org/spif#",
        "sr": "http://www.openrdf.org/config/repository/sail#",
        "ssno": "https://matthiasprobst.github.io/ssno#",
        "wgs": "http://www.w3.org/2003/01/geo/wgs84_pos#",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }

    @property
    @abstractmethod
    def graph(self) -> rdflib.Graph:
        """Return graph for the metadata store."""

    # @property
    # def query(self):
    #     return SparqlQuery(self.graph)


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

    # @property
    # def query(self) -> RemoteSparqlQuery:
    #     """Return graph for the DbPedia metadata store."""
    #     try:
    #         from SPARQLWrapper import SPARQLWrapper, JSON
    #     except ImportError:
    #         raise ImportError("Please install SPARQLWrapper to use this class: pip install SPARQLWrapper")
    #     sparql = SPARQLWrapper(self.endpoint)
    #     sparql.setReturnFormat(JSON)
    #     return RemoteSparqlQuery(sparql)

    def upload_file(self, filename: Union[str, pathlib.Path]) -> bool:
        """Uploads a file to the remote SPARQL endpoint."""
        raise NotImplementedError("Remote SPARQL Store does not support file uploads.")


class StoreManager:
    """Store manager that manages the interaction between stores."""

    def __init__(self, stores: Dict[str, Store] = None):
        self._stores: Dict[str, DataStore] = stores if stores is not None else {}

    def __getattr__(self, item) -> Store:
        """Allows access to stores as attributes."""
        if item in self.stores:
            return self.stores[item]
        return super().__getattribute__(item)

    def __len__(self):
        """Returns the number of stores managed."""
        return len(self.stores)

    def __repr__(self):
        """String representation of the DataStoreManager."""
        store_names = ", ".join(self.stores.keys())
        return f"{self.__class__.__name__}(stores=[{store_names}])"

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

class InMemoryRDFStore(RDFStore):
    """In-memory RDF database that can upload files and return a combined graph."""

    _expected_file_extensions = {".ttl", ".rdf", ".jsonld", ".nt", ".xml", ".n3"}

    def __init__(
            self,
            data_dir: Union[str, pathlib.Path],
            recursive_exploration: bool = False,
            formats=None
    ):
        if formats is None:
            formats = self._expected_file_extensions
        elif isinstance(formats, str):
            formats = {f".{formats.lstrip('.')}", }
        elif isinstance(formats, (list, set, tuple)):
            formats = {f".{fmt.lstrip('.')}" for fmt in formats}
        else:
            raise ValueError("formats must be a string or a list/set/tuple of strings.")

        for _fmt in formats:
            if _fmt not in self._expected_file_extensions:
                raise ValueError(f"File format '{_fmt}' not supported.")

        self._expected_file_extensions = formats
        self._data_dir = pathlib.Path(data_dir).resolve()
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._recursive_exploration = recursive_exploration
        self._filenames = []
        self._graphs = {}
        self._combined_graph = rdflib.Graph()
        self.update()

    @property
    def data_dir(self) -> pathlib.Path:
        """Returns the data directory where files are stored."""
        return self._data_dir

    def update(self):
        for _ext in self._expected_file_extensions:
            if self._recursive_exploration:
                self._filenames.extend([f.resolve().absolute() for f in self.data_dir.rglob(f"*{_ext}")])
            else:
                self._filenames.extend([f.resolve().absolute() for f in self.data_dir.glob(f"*{_ext}")])
        self._filenames = list(set(self._filenames))  # remove duplicates
        for filename in self._filenames:
            self._add_to_graph(filename)

    @property
    def filenames(self):
        """Returns the list of filenames uploaded to the store."""
        return self._filenames

    def upload_file(self, filename) -> bool:
        filename = pathlib.Path(filename).resolve().absolute()
        if not filename.exists():
            raise FileNotFoundError(f"File {filename} not found.")
        if filename.suffix not in self._expected_file_extensions:
            raise ValueError(f"File type {filename.suffix} not supported.")
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


class GraphDB(RemoteSparqlStore):
    """GraphDB RDF database store."""

    def __init__(self, endpoint: str, repository: str, username: str = None, password: str = None):
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

    def upload_file(self, filename: Union[str, pathlib.Path]) -> bool:
        """Uploads an RDF file to das GraphDB-Repository."""
        filename = pathlib.Path(filename).resolve().absolute()
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
