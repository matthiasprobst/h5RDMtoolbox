"""Catalog query interfaces, execution and result models."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd
from rdflib import Graph

from .abstracts import RDFStore, Store
from .stores.sparql import RemoteSparqlStore
from .utils import sparql_json_to_dataframe, sparql_result_to_df

logger = logging.getLogger("h5rdmtoolbox.catalog")


class AbstractQuery(ABC):
    """Interface for executing a query against a catalog store."""

    @abstractmethod
    def execute(self, store: "Store") -> "QueryResult":
        """Executes the query."""


class QueryResult:
    """Query output with optional bindings and a derived RDF graph.

    Parameters
    ----------
    query : AbstractQuery
        Query that produced the result.
    data : Any
        Returned data, usually a DataFrame or an RDF graph.
    bindings : Any, optional
        Raw RDF variable bindings.
    description : str, optional
        Human-readable description of the query result.
    derived_graph : rdflib.Graph, optional
        Graph produced by a graph-returning query such as CONSTRUCT.
    """

    def __init__(
        self,
        query: AbstractQuery,
        data: Any,
        bindings: Any = None,
        description: Optional[str] = None,
        derived_graph: Optional[Graph] = None,
    ):
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
    """Data and metadata returned by a federated catalog lookup."""

    data: Any
    metadata: Dict


class Query(AbstractQuery, ABC):
    """Query text and description shared by concrete query types.

    Parameters
    ----------
    query : str
        Query text interpreted by the concrete implementation.
    description : str, optional
        Human-readable description of the query.
    """

    def __init__(self, query, description=None):
        self.query = query
        self.description = description

    def __eq__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self.query == other.query and self.description == other.description

    def __repr__(self):
        description_repr = self.description or ""
        return f'{self.__class__.__name__}(query="{self.query}", description="{description_repr}")'


class MetadataStoreQuery(Query, ABC):
    """RDF Store Query interface."""

    @abstractmethod
    def execute(
        self, store: "Store", named_graph: Optional[str] = None
    ) -> "QueryResult":
        """Executes the query against the given metadata store with optional named graph."""


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
                derived_graph=derived_graph,
            )
        return QueryResult(
            query=self,
            data=sparql_result_to_df(bindings),
            bindings=bindings,
            description=self.description,
            derived_graph=derived_graph,
        )


class RemoteSparqlQuery(MetadataStoreQuery):
    """SPARQL query executed through a remote endpoint's client wrapper."""

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
        return QueryResult(query=self, data=data, description=self.description)
