import logging
import pathlib
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Union, Any, Dict

import rdflib
from ontolutils.ex import dcat
from rdflib.graph import _TripleType


@lru_cache(maxsize=1)
def _get_pyshacl():
    try:
        import pyshacl as sh

        return sh
    except ImportError as e:
        raise ImportError("pyshacl is required but not installed") from e


logger = logging.getLogger("h5rdmtoolbox.catalog")


class Store(ABC):
    """Store interface."""

    @abstractmethod
    def upload_file(
            self,
            filename: Union[str, pathlib.Path],
            validate: bool = True,
            skip_unsupported: bool = False,
    ) -> Any:
        """Uploads a file to the store."""

    def __repr__(self):
        """String representation of the Store."""
        return f"{self.__class__.__name__}()"


class DataStore(Store, ABC):
    """Data store interface (concrete implementations can be sql or non sql databases)."""

    def upload_file(
            self,
            filename: Union[str, pathlib.Path] = None,
            distribution: dcat.Distribution = None,
            validate: bool = True,
            skip_unsupported: bool = False,
    ) -> dcat.Distribution:
        """Insert data into the data store. Source can be either a filename or a dcat.Distribution."""
        if filename is None and distribution is None:
            raise ValueError("Either filename or distribution must be provided.")
        if filename is not None and distribution is not None:
            raise ValueError("Only one of filename or distribution can be provided.")
        if filename is not None:
            download_url = str(pathlib.Path(filename).resolve().absolute().as_uri())
            distribution = dcat.Distribution(
                id=download_url,
                download_URL=download_url
            )
        self._upload_file(
            distribution=distribution,
            validate=validate,
            skip_unsupported=skip_unsupported
        )
        return distribution

    @abstractmethod
    def _upload_file(
            self,
            distribution: dcat.Distribution,
            validate: bool = True,
            skip_unsupported: bool = False,
    ):
        """Insert data into the data store. Source can be either a filename or a dcat.Distribution."""


class MetadataStore(Store, ABC):
    """Metadata database interface using."""

    __populate_on_init__ = False
    __shacl_shapes__: Dict[str, rdflib.Graph] = {}

    @abstractmethod
    def _upload_file(
            self,
            filename: Union[str, pathlib.Path],
            validate: bool = True,
            skip_unsupported: bool = False,
    ) -> bool:
        """Insert data into the data store."""

    @abstractmethod
    def _upload_triple(self, triple: _TripleType) -> bool:
        """Insert a triple into the data store."""

    def upload_triple(self, triple: _TripleType):
        """Insert a triple into the data store.

        Parameters
        ----------
        triple : _TripleType
            A triple to insert into the data store.

        """
        return self._upload_triple(triple)

    @abstractmethod
    def _upload_data(self, data: str, format: str) -> bool:
        """Insert rdf data, e.g. in form of a TURTLE string, into the data store."""

    def upload_data(self, data: str, format: str):
        """Insert rdf data, e.g. in form of a TURTLE string, into the data store.

        Parameters
        ----------
        data : str
            RDF data, e.g. in form of a TURTLE string, to insert into the data store.

        """
        return self._upload_data(data=data, format=format)

    def upload_file(
            self,
            filename: Union[str, pathlib.Path],
            validate: bool = True,
            skip_unsupported: bool = False,
    ) -> bool:
        """Insert data into the data store."""
        if self.__shacl_shapes__:
            self._validate_filename(filename)
        return self._upload_file(
            filename, validate=validate, skip_unsupported=skip_unsupported
        )

    def _validate_filename(self, filename: Union[str, pathlib.Path]) -> bool:
        g = rdflib.Graph().parse(source=filename)
        for shacl_name, shacl_shape in self.__shacl_shapes__.items():
            logger.debug(
                f"Validating file {filename} against SHACL shape {shacl_name}."
            )
            conforms, results_graph, results_text = _get_pyshacl().validate(
                data_graph=g,
                shacl_graph=shacl_shape,
                inference="rdfs",
                abort_on_first=False,
                meta_shacl=False,
                debug=False,
            )
            if not conforms:
                logger.error(
                    f"SHACL validation failed for file {filename}:\n{results_text}"
                )
                raise ValueError(
                    f"SHACL validation failed for file {filename}:\n{results_text}"
                )
        return True

    def register_shacl_shape(
            self,
            name: str,
            *,
            shacl_source: Union[str, pathlib.Path] = None,
            shacl_data: Union[str, rdflib.Graph] = None,
    ):
        """Register SHACL shapes for validation."""
        if shacl_source is not None and shacl_data is not None:
            raise ValueError("Cannot provide both shacl_source and shacl_data.")
        if name in self.__shacl_shapes__:
            raise ValueError(
                f"SHACL shape with name '{name}' is already registered. Call drop_shacl_shap()) first."
            )
        if shacl_data is not None:
            if isinstance(shacl_data, rdflib.Graph):
                shacl_graph = shacl_data
            else:
                shacl_graph = rdflib.Graph()
                shacl_graph.parse(data=shacl_data, format="ttl")
        elif shacl_source is not None:
            shacl_graph = rdflib.Graph()
            shacl_graph.parse(source=shacl_source)
        else:
            raise ValueError("Must provide either shacl_source or shacl_data.")
        self.__shacl_shapes__[name] = shacl_graph

    def drop_shacl_shap(self, shacl_name):
        """Drop registered SHACL shape."""
        if shacl_name in self.__shacl_shapes__:
            del self.__shacl_shapes__[shacl_name]


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
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }

    @property
    @abstractmethod
    def graph(self) -> rdflib.Graph:
        """Return graph for the metadata store."""

    @abstractmethod
    def reset(self, *args, **kwargs):
        """Resets the store/database."""

    def populate(self):
        pass
