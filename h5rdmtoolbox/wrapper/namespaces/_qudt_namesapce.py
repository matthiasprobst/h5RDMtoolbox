"""Namespace for QUDT units. Note, that it must be designed a bit differently than the other namespaces, because
dash is not allowed in python variable names."""

from rdflib.namespace import Namespace
from rdflib.term import URIRef


class _QUDT_UNIT:
    """Work in progress. Add units whenever you come across them in your code. Thanks!."""
    # uri = "https://qudt.org/vocav/unit/"
    M_PER_SEC = URIRef("https://qudt.org/vocab/unit/M-PER-SEC")
    M_PER_SEC2 = URIRef("https://qudt.org/vocab/unit/M-PER-SEC2")
    M = URIRef("https://qudt.org/vocab/unit/M")
    SEC = URIRef("https://qudt.org/vocab/unit/SEC")

    _NS = Namespace("https://qudt.org/vocab/unit/")


class _HasQuantityKind:
    # uri = "https://qudt.org/vocab/quantitykind/"
    Period = URIRef("https://qudt.org/vocab/quantitykind/Period")
    Time = URIRef("https://qudt.org/vocab/quantitykind/Time")
    Acceleration = URIRef("https://qudt.org/vocab/quantitykind/Acceleration")
    LinearAcceleration = URIRef("https://qudt.org/vocab/quantitykind/LinearAcceleration")
    Velocity = URIRef("https://qudt.org/vocab/quantitykind/Velocity")

    _NS = Namespace("https://qudt.org/vocab/quantitykind/")


QUDT_UNIT = _QUDT_UNIT()
HAS_QKIND = _HasQuantityKind()
