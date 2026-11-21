from typing import Callable, Optional, Any

from pydantic import BaseModel, Field


class RDFMappingEntry(BaseModel):
    predicate: Optional[Any] = Field(None, description="Predicate IRI or rdflib term")
    object: Optional[Callable[[Any], Any]] = Field(None, description="Function to generate object value")

    class Config:
        arbitrary_types_allowed = True
