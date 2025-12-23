from abc import ABC

from .query import Query


class DataStoreQuery(Query, ABC):
    """Data store query interface (concrete implementations can be sql or non sql query)."""
