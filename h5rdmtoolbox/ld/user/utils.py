import rdflib
from rdflib import URIRef

from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES


def to_uriref(value: str, blank_node_iri_base: str = None) -> URIRef:
    """Convert a value to a URIRef, handling blank nodes if necessary."""
    if value.startswith("_:") and blank_node_iri_base:
        value = blank_node_iri_base + value[2:]
    return URIRef(value)


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
                        graph.add((obj_uri, predicate_uri, rdflib.Literal(av)))
                type_uri = mapping.get('type')
                if type_uri:
                    graph.add((obj_uri, rdflib.RDF.type, rdflib.URIRef(type_uri)))
