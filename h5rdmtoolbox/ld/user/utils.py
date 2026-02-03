import hashlib
from typing import Union

import rdflib

from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES
from ..utils import to_literal


def bnode_from_string(s: str, bits: int = 64, blank_node_iri_base=None) -> rdflib.URIRef:
    """Create a deterministic blank node from a string."""
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    number = int.from_bytes(digest[:bits // 8], "big")
    return to_uriref(f"_:{str(number)}", blank_node_iri_base)


def to_uriref(value: str, blank_node_iri_base: str = None) -> Union[rdflib.URIRef, rdflib.BNode]:
    """Convert a value to a URIRef, handling blank nodes if necessary."""
    if isinstance(value, rdflib.BNode):
        if blank_node_iri_base is not None:
            return rdflib.URIRef(blank_node_iri_base + str(value))
        return value
    if isinstance(value, rdflib.URIRef):
        return value
    if value.startswith("_:"):
        if blank_node_iri_base is not None:
            value = blank_node_iri_base + value[2:]
            return rdflib.URIRef(value)
        return rdflib.BNode(value[2:])
    if value.startswith("http://") or value.startswith("https://") or value.startswith("urn:"):
        return rdflib.URIRef(value)
    raise ValueError(f"Cannot convert value '{value}' to URIRef")


def apply_rdf_mappings(obj, obj_uri, graph, rdf_mappings):
    for ak, av in obj.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            if ak in rdf_mappings:
                mapping = rdf_mappings[ak]
                predicate_uri = rdflib.URIRef(mapping['predicate'])
                if predicate_uri:
                    object_uri = mapping.get('object')
                    if object_uri:
                        if callable(object_uri):
                            object_uri = str(object_uri(av, obj.attrs))
                            if object_uri is None:
                                return
                        graph.add((obj_uri, predicate_uri, rdflib.URIRef(object_uri)))
                    else:
                        graph.add((obj_uri, predicate_uri, to_literal(av)))
                type_uri = mapping.get('type')
                if type_uri:
                    graph.add((obj_uri, rdflib.RDF.type, rdflib.URIRef(type_uri)))
