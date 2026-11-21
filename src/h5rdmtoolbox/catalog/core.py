"""Compatibility exports for catalog stores, queries and result types.

Implementations live in the query, store-manager and storage modules. Retained
catalog APIs resolve to those same classes; the SQL adapter was removed in 3.0.
"""

from .abstracts import DataStore, MetadataStore, RDFStore, Store
from .queries import (
    AbstractQuery,
    FederatedQueryResult,
    MetadataStoreQuery,
    Query,
    QueryResult,
    RemoteSparqlQuery,
    SparqlQuery,
)
from .store_manager import StoreManager
from .stores.memory import InMemoryRDFStore
from .stores.sparql import GraphDB, RemoteSparqlStore, RSX, SH, _format_shacl_report

__all__ = [
    "_format_shacl_report",
    "AbstractQuery",
    "DataStore",
    "FederatedQueryResult",
    "GraphDB",
    "InMemoryRDFStore",
    "MetadataStore",
    "MetadataStoreQuery",
    "Query",
    "QueryResult",
    "RDFStore",
    "RemoteSparqlQuery",
    "RemoteSparqlStore",
    "RSX",
    "SH",
    "SparqlQuery",
    "Store",
    "StoreManager",
]
