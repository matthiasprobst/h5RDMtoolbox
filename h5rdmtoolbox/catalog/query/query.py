from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict
from typing import Optional

from rdflib import Graph

from ..stores import Store


class AbstractQuery(ABC):

    @abstractmethod
    def execute(self, store: Store) -> "QueryResult":
        """Executes the query."""


class QueryResult:

    def __init__(self, query: AbstractQuery, data: Any, description: Optional[str] = None,
                 derived_graph: Optional[Graph] = None):
        self.query = query
        self.data = data
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
