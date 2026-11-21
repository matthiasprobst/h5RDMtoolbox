"""Small ontology models for testing toolbox RDF serialization."""
from typing import Optional

import rdflib
from ontolutils import namespaces, urirefs
from ontolutils.ex.dcat import Dataset
from ontolutils.ex.skos import Concept, ConceptScheme
from ontolutils.utils.qudt_units import qudt_lookup
from pydantic import ConfigDict, Field, field_validator

SSNO = rdflib.Namespace("https://matthiasprobst.github.io/ssno#")


@namespaces(ssno=str(SSNO))
@urirefs(StandardNameTable="ssno:StandardNameTable", dataset="ssno:dataset")
class StandardNameTable(ConceptScheme):
    dataset: Optional[Dataset] = None


@namespaces(ssno=str(SSNO))
@urirefs(StandardName="ssno:StandardName", standardName="ssno:standardName",
         unit="ssno:unit", standardNameTable="ssno:standardNameTable")
class StandardName(Concept):
    model_config = ConfigDict(populate_by_name=True)
    standardName: str = Field(alias="standard_name")
    unit: str
    standardNameTable: Optional[StandardNameTable] = Field(default=None, alias="standard_name_table")

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value):
        value = str(value)
        return str(qudt_lookup.get(value, value))

    def __str__(self):
        return self.standardName
