import logging
from abc import ABC

import pandas as pd
import rdflib

from .query import Query, QueryResult
from .utils import sparql_json_to_dataframe
from ..stores import RDFStore, RemoteSparqlStore

logger = logging.getLogger("h5rdmtoolbox.catalog")


def parse_literal(literal):
    if isinstance(literal, rdflib.Literal):
        return literal.value
    if isinstance(literal, rdflib.URIRef):
        return str(literal)
    return literal


def sparql_result_to_df(bindings):
    return pd.DataFrame([{str(k): parse_literal(v) for k, v in binding.items()} for binding in bindings])


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
                description=self.description,
                derived_graph=derived_graph
            )
        return QueryResult(
            query=self,
            data=sparql_result_to_df(bindings),
            description=self.description,
            derived_graph=derived_graph
        )


class RemoteSparqlQuery(MetadataStoreQuery):

    def execute(self, store: RemoteSparqlStore, *args, **kwargs) -> QueryResult:
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
