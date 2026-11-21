"""Compatibility exports for catalog stores, queries and result types.

Implementations live in the query, store-manager and storage modules. Existing
imports from this module continue to resolve to those same classes.
"""

from .abstracts import DataStore, MetadataStore, RDFStore, Store
from .queries import (
    AbstractQuery,
    DataStoreQuery,
    FederatedQueryResult,
    MetadataStoreQuery,
    Query,
    QueryResult,
    RemoteSparqlQuery,
    SparqlQuery,
    SQLQuery,
)
from .store_manager import StoreManager
from .stores.memory import InMemoryRDFStore
from .stores.sparql import GraphDB, RemoteSparqlStore, RSX, SH, _format_shacl_report
from .stores.sql import DatabaseResource, HDF5SqlDB

__all__ = [
    "_format_shacl_report",
    "AbstractQuery",
    "DatabaseResource",
    "DataStore",
    "DataStoreQuery",
    "FederatedQueryResult",
    "GraphDB",
    "HDF5SqlDB",
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
    "SQLQuery",
    "Store",
    "StoreManager",
]
