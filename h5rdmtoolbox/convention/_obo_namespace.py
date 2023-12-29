from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef


class OBO(DefinedNamespace):
    # uri = "https://w3id.org/nfdi4ing/metadata4ing#"
    # Generated with h5rdmtoolbox.data.m4i.generate_namespace_file()
    # Date: 2023-12-29 14:07:43.511726
    BFO_0000015: URIRef  # ['Prozess', 'process']
    BFO_0000017: URIRef  # ['realisierbare EntitÃ¤t', 'realizable entity']
    BFO_0000050: URIRef  # ['Teil von', 'part of']
    BFO_0000051: URIRef  # ['has part', 'hat Teil']
    BFO_0000054: URIRef  # ['realisiert in', 'realized in']
    BFO_0000055: URIRef  # ['realisiert', 'realizes']
    BFO_0000063: URIRef  # ['ist Voraussetzung fÃ¼r Schritt', 'precedes']
    RO_0000056: URIRef  # ['ist beteiligt an', 'participates in']
    RO_0000057: URIRef  # ['has participant', 'hat Teilnehmer']
    RO_0002090: URIRef  # ['immediately precedes', 'ist unmittelbare Voraussetzung fÃ¼r Schritt']
    RO_0002224: URIRef  # ['beginnt mit', 'starts with']
    RO_0002230: URIRef  # ['endet mit', 'ends with']
    RO_0002233: URIRef  # ['has input', 'hat Input']
    RO_0002234: URIRef  # ['has output', 'hat Output']
    RO_0002352: URIRef  # ['Input von', 'input of']
    RO_0002353: URIRef  # ['Output von', 'output of']

    _NS = Namespace("http://purl.obolibrary.org/obo/")
