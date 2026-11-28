from datetime import datetime
from typing import Optional, List, Union

from pydantic import Field

from ontolutils import Thing, LangString, namespaces, urirefs
from ontolutils.typing import AnyThingOrList

_NS = "http://www.w3.org/2004/02/skos/core#"


@namespaces(skos=_NS,
            dcterms="http://purl.org/dc/terms/",
            prov="http://www.w3.org/ns/prov#")
@urirefs(Note='skos:Note',
         value='rdf:value',
         created='dcterms:created',
         wasRevisionOf='prov:wasRevisionOf',
         creator='dcterms:creator')
class Note(Thing):
    value: LangString = Field(...)
    created: Optional[datetime] = Field(default=None)
    wasRevisionOf: Optional[Thing] = Field(default=None, alias="wasRevisionOf")
    creator: Optional[AnyThingOrList] = Field(default=None)


@namespaces(skos=_NS)
@urirefs(ConceptScheme='skos:ConceptScheme',
         hasTopConcept='skos:hasTopConcept'
         )
class ConceptScheme(Thing):
    """Implementation of skos:ConceptScheme"""
    hasTopConcept: Optional[Union['Concept', List['Concept']]] = Field(default=None, alias="has_top_concept")


@namespaces(skos=_NS)
@urirefs(Concept='skos:Concept',
         prefLabel='skos:prefLabel',
         altLabel='skos:altLabel',
         hiddenLabel='skos:hiddenLabel',
         definition='skos:definition',
         note='skos:note',
         scopeNote='skos:scopeNote',
         editorialNote='skos:editorialNote',
         changeNote='skos:changeNote',
         inScheme='skos:inScheme',
         example='skos:example')
class Concept(Thing):
    """Implementation of skos:Concept"""

    prefLabel: Optional[Union[LangString, List[LangString]]] = Field(default=None, alias="pref_label")
    altLabel: Optional[Union[LangString, List[LangString]]] = Field(default=None, alias="alt_label")
    hiddenLabel: Optional[Union[LangString, List[LangString]]] = Field(default=None, alias="hidden_label")
    definition: Optional[Union[LangString, List[LangString]]] = Field(default=None)
    note: Optional[Union[LangString, Note, List[Union[LangString, Note]]]] = Field(default=None)
    scopeNote: Optional[Union[LangString, Note, List[Union[LangString, Note]]]] = Field(default=None,
                                                                                        alias="scope_note")
    editorialNote: Optional[Union[LangString, Note, List[Union[LangString, Note]]]] = Field(default=None,
                                                                                            alias="editorial_note")
    changeNote: Optional[Union[LangString, Note, List[Union[LangString, Note]]]] = Field(default=None,
                                                                                         alias="change_note")
    inScheme: Optional[Union[ConceptScheme, List[ConceptScheme]]] = Field(default=None, alias="in_scheme")
    example: Optional[Union[LangString, List[LangString]]] = Field(default=None)


ConceptScheme.model_rebuild()
