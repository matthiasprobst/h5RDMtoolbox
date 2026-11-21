"""Remote SPARQL and GraphDB storage adapters."""

import logging
import pathlib
from typing import Any, Dict, Union

import rdflib
import requests
from rdflib import Graph, Namespace
from rdflib.graph import _TripleType
from rdflib.namespace import RDF

from ..abstracts import MetadataStore
from ..utils import USER_AGENT_HEADER

SH = Namespace("http://www.w3.org/ns/shacl#")
RSX = Namespace("http://rdf4j.org/shacl-extensions#")
logger = logging.getLogger("h5rdmtoolbox.catalog")


class RemoteSparqlStore(MetadataStore):
    """Metadata store accessed through a SPARQL endpoint.

    Parameters
    ----------
    endpoint_url : str
        URL of the remote SPARQL endpoint.
    return_format : str, optional
        Response format passed to SPARQLWrapper.
    """

    def __init__(self, endpoint_url, return_format: str = None):
        try:
            from SPARQLWrapper import SPARQLWrapper
        except ImportError:
            raise ImportError(
                "Please install SPARQLWrapper to use this class: 'pip install SPARQLWrapper'"
            )

        self._wrapper = SPARQLWrapper(endpoint_url)
        if return_format is not None:
            self._wrapper.setReturnFormat(return_format)
        self._wrapper.addCustomHttpHeader("User-Agent", USER_AGENT_HEADER["User-Agent"])

    @property
    def wrapper(self):
        return self._wrapper

    def _upload_file(
        self,
        filename: Union[str, pathlib.Path],
        validate: bool = False,
        skip_unsupported: bool = False,
    ) -> bool:
        """Uploads a file to the remote SPARQL endpoint."""
        raise NotImplementedError("Remote SPARQL Store does not support file uploads.")

    def _upload_triple(self, triple: _TripleType) -> bool:
        raise NotImplementedError(
            "Remote SPARQL Store does not support triple uploads."
        )

    def _upload_data(self, data: str, format: str) -> bool:
        raise NotImplementedError("Remote SPARQL Store does not support data uploads.")


class GraphDB(RemoteSparqlStore):
    """GraphDB RDF database store."""

    __supports_named_graphs__: bool = True
    __supported_file_extensions__ = {".ttl", ".rdf", ".jsonld"}

    def __init__(
        self, endpoint: str, repository: str, username: str = None, password: str = None
    ):
        super().__init__(f"{endpoint}/repositories/{repository}")
        try:
            from SPARQLWrapper import SPARQLWrapper, JSON
        except ImportError:
            raise ImportError(
                "Please install SPARQLWrapper to use this class: pip install SPARQLWrapper"
            )
        self._endpoint = endpoint
        self._repository = repository
        self._username = username
        self._password = password
        self._wrapper.setReturnFormat(JSON)
        if self.username and self.password:
            self._wrapper.setCredentials(self.username, self.password)

        repo_info = self.get_repository_info(self.repository)
        if not repo_info:
            logger.info(
                f"The repository '{self.repository}' does not exist. "
                "Call create_repository('config.ttl') with a valid configuration "
                "('config.ttl') file to create it."
            )

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

    def _upload_triple(self, triple: _TripleType) -> bool:
        """Uploads a single triple to the GraphDB-Repository."""
        url = f"{self.endpoint}/repositories/{self.repository}/statements"
        s, p, o = triple

        # Normalize incoming terms into rdflib terms (URIRef, Literal, BNode)
        from rdflib import URIRef, Literal, BNode

        def _normalize_term(t):
            # If already an rdflib Node, return as-is
            if isinstance(t, rdflib.term.Node):
                return t
            # Strings: strip angle brackets, detect blank nodes and absolute URIs
            if isinstance(t, str):
                st = t.strip()
                if st.startswith("<") and st.endswith(">"):
                    st = st[1:-1]
                if st.startswith("_:"):
                    return BNode(st[2:])
                # Treat absolute URIs (containing scheme) as URIRefs
                if (
                    "://" in st
                    or st.startswith("http:")
                    or st.startswith("https:")
                    or st.startswith("urn:")
                ):
                    return URIRef(st)
                # Fallback to Literal for anything else
                return Literal(st)
            # For other types, try to convert to Literal
            return Literal(t)

        gs = Graph()
        gs.add((_normalize_term(s), _normalize_term(p), _normalize_term(o)))

        # Serialize to N-Triples to avoid needing a base URI (GraphDB accepts this)
        data = gs.serialize(format="nt")
        headers = {"Content-Type": "application/n-triples; charset=utf-8"}
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.post(
            url, data=data.encode("utf-8"), headers=headers, auth=auth
        )
        if response.status_code in (200, 201, 204):
            return True
        elif response.status_code == 500:
            readable_shacl_errors = _format_shacl_report(response.text)
            raise ValueError(f"SHACL validation failed:\n\n{readable_shacl_errors}")
        else:
            raise RuntimeError(f"Upload failed: {response.status_code} {response.text}")

    def _upload_file(
        self,
        filename: Union[str, pathlib.Path],
        validate: bool = False,
        skip_unsupported: bool = False,
    ) -> bool:
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
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.post(url, data=data, headers=headers, auth=auth)
        if response.status_code in (200, 201, 204):
            return True
        elif response.status_code == 500:
            readable_shacl_errors = _format_shacl_report(response.text)
            raise ValueError(f"SHACL validation failed:\n\n{readable_shacl_errors}")
        else:
            raise RuntimeError(f"Upload failed: {response.status_code} {response.text}")

    def create_repository(self, config_path: Union[str, pathlib.Path]) -> bool:
        """Creates a GraphDB repository using a configuration file (repo-config.ttl)."""
        config_path = pathlib.Path(config_path).resolve().absolute()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}.")
        url = f"{self.endpoint}/rest/repositories"
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        with open(config_path, "rb") as f:
            files = {"config": (config_path.name, f, "application/x-turtle")}
            response = requests.post(url, files=files, auth=auth)
        if response.status_code in (201, 204):
            return True
        else:
            raise RuntimeError(
                f"Repository konnte nicht angelegt werden: {response.status_code} {response.text}"
            )

    def list_repositories(self) -> Any:
        """Lists all repositories in the GraphDB instance."""
        url = f"{self.endpoint}/rest/repositories"
        headers = {"Accept": "application/json"}
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.get(url, headers=headers, auth=auth)
        if response.status_code == 200:
            return response.json()
        return None

    def get_repository_info(self, repository=None) -> Dict:
        """Returns information about a specific repository."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}"
        headers = {"Accept": "application/json"}
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.get(url, headers=headers, auth=auth)

        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            logger.debug(f"Repository '{repo}' does not exist.")
            return {}
        if response.status_code == 401:
            raise RuntimeError(
                f"Unauthorized access to repository '{repo}'. Check your credentials."
            )
        if response.status_code == 403:
            raise RuntimeError(
                f"Forbidden access to repository '{repo}'. Check your permissions."
            )
        raise RuntimeError(
            f"Error fetching repository info: {response.status_code} {response.text}"
        )

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
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            try:
                data = response.json()
                return int(data.get(key, 0))
            except Exception:
                raise RuntimeError(f"Error parsing the triple number: {response.text}")
        else:
            raise RuntimeError(
                f"Error fetching the triple number: {response.status_code} {response.text}"
            )

    def restart_repository(self, repository: str = None) -> bool:
        """Restarts a repository in the GraphDB instance."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}/restart"
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.post(url, auth=auth)
        if response.status_code in (200, 204):
            return True
        else:
            raise RuntimeError(
                f"Error restarting the repository: {response.status_code} {response.text}"
            )

    def delete_repository(self, repository: str = None) -> bool:
        """Deletes a repository from the GraphDB instance."""
        repo = repository or self.repository
        url = f"{self.endpoint}/rest/repositories/{repo}"
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        response = requests.delete(url, auth=auth)
        if response.status_code in (200, 204):
            return True
        else:
            raise RuntimeError(
                f"Error deleting the repository: {response.status_code} {response.text}"
            )

    def _validate_filename(self, *args, **kwargs):
        return True

    def register_shacl_shape(
        self,
        name: str,
        *,
        shacl_source: Union[str, pathlib.Path] = None,
        shacl_data: Union[str, rdflib.Graph] = None,
    ):
        """Register SHACL shapes for validation."""
        super().register_shacl_shape(
            name, shacl_source=shacl_source, shacl_data=shacl_data
        )
        if shacl_source is None and shacl_data is None:
            raise ValueError("Either shacl_source or shacl_data must be provided.")
        if shacl_source is not None:
            if isinstance(shacl_source, rdflib.Graph):
                shacl_data = shacl_source.serialize(format="turtle")
            else:
                g = rdflib.Graph().parse(source=shacl_source)
                shacl_data = g.serialize(format="turtle")
        if not isinstance(shacl_data, str):
            raise ValueError("shacl_data must be a string in Turtle format.")

        headers = {"Content-Type": "text/turtle"}
        SHAPES_GRAPH = "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
        params = {"context": f"<{SHAPES_GRAPH}>"}
        url = f"{self.endpoint}/repositories/{self.repository}/statements"
        # ulr = f"{self.endpoint}/rest/repositories/{self.repository}/validate/text",
        resp = requests.post(
            url,
            data=shacl_data.encode("utf-8"),
            headers=headers,
            params=params,
            auth=(self.username, self.password)
            if self.username and self.password
            else None,
        )
        resp.raise_for_status()

    def _post_update(self, update):
        url = f"{self.endpoint}/repositories/{self.repository}/statements"
        headers = {"Content-Type": "application/sparql-update"}
        auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        r = requests.post(
            url,
            data=update.encode("utf-8"),
            headers=headers,
            auth=auth,
        )
        if not r.ok:
            raise RuntimeError(
                f"GraphDB SPARQL update failed (status {r.status_code}):\n{r.text}"
            )


def _format_shacl_report(turtle_text: str) -> str:
    g = Graph()
    g.parse(data=turtle_text, format="turtle")

    messages = []

    for result in g.subjects(RDF.type, SH.ValidationResult):
        focus = g.value(result, SH.focusNode)
        path = g.value(result, SH.resultPath)
        value = g.value(result, SH.value)
        severity = g.value(result, SH.resultSeverity)
        component = g.value(result, SH.sourceConstraintComponent)

        messages.append(
            f"- Resource: {focus}\n"
            f"  Property: {path}\n"
            f"  Invalid value: {value}\n"
            f"  Constraint: {component.split('#')[-1] if component else 'Unknown'}\n"
            f"  Severity: {severity.split('#')[-1] if severity else 'Unknown'}"
        )

    return "\n\n".join(messages) if messages else "No SHACL violations found."
