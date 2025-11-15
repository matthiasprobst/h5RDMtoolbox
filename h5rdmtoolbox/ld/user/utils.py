from rdflib import URIRef


def to_uriref(value: str, blank_node_iri_base: str = None) -> URIRef:
    """Convert a value to a URIRef, handling blank nodes if necessary."""
    if value.startswith("_:") and blank_node_iri_base:
        value = blank_node_iri_base + value[2:]
    return URIRef(value)
