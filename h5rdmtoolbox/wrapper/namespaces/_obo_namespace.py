from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef


class LanguageExtension:
    pass

class OBO(DefinedNamespace):
    # uri = "https://w3id.org/nfdi4ing/metadata4ing#"
    # Generated with h5rdmtoolbox.data.m4i.generate_namespace_file()
    # Date: 2024-02-28 07:59:08.870462
    BFO_0000015: URIRef  # ['Prozess', 'process']
    BFO_0000017: URIRef  # ['realisierbare Entität', 'realizable entity']
    BFO_0000050: URIRef  # ['Teil von', 'part of']
    BFO_0000051: URIRef  # ['has part', 'hat Teil']
    BFO_0000054: URIRef  # ['realisiert in', 'realized in']
    BFO_0000055: URIRef  # ['realisiert', 'realizes']
    BFO_0000063: URIRef  # ['ist Voraussetzung für Schritt', 'precedes']
    RO_0000056: URIRef  # ['ist beteiligt an', 'participates in']
    RO_0000057: URIRef  # ['has participant', 'hat Teilnehmer']
    RO_0002090: URIRef  # ['immediately precedes', 'ist unmittelbare Voraussetzung für Schritt']
    RO_0002224: URIRef  # ['beginnt mit', 'starts with']
    RO_0002230: URIRef  # ['endet mit', 'ends with']
    RO_0002233: URIRef  # ['has input', 'hat Input']
    RO_0002234: URIRef  # ['has output', 'hat Output']
    RO_0002352: URIRef  # ['Input von', 'input of']
    RO_0002353: URIRef  # ['Output von', 'output of']

    _NS = Namespace("http://purl.obolibrary.org/obo/")

de = LanguageExtension()

setattr(de, "Prozess", OBO.BFO_0000015)
setattr(OBO, "process", OBO.BFO_0000015)
setattr(de, "realisierbare_Entität", OBO.BFO_0000017)
setattr(OBO, "realizable_entity", OBO.BFO_0000017)
setattr(de, "Teil_von", OBO.BFO_0000050)
setattr(OBO, "part_of", OBO.BFO_0000050)
setattr(OBO, "has_part", OBO.BFO_0000051)
setattr(de, "hat_Teil", OBO.BFO_0000051)
setattr(de, "realisiert_in", OBO.BFO_0000054)
setattr(OBO, "realized_in", OBO.BFO_0000054)
setattr(de, "realisiert", OBO.BFO_0000055)
setattr(OBO, "realizes", OBO.BFO_0000055)
setattr(de, "ist_Voraussetzung_für_Schritt", OBO.BFO_0000063)
setattr(OBO, "precedes", OBO.BFO_0000063)
setattr(de, "ist_beteiligt_an", OBO.RO_0000056)
setattr(OBO, "participates_in", OBO.RO_0000056)
setattr(OBO, "has_participant", OBO.RO_0000057)
setattr(de, "hat_Teilnehmer", OBO.RO_0000057)
setattr(OBO, "immediately_precedes", OBO.RO_0002090)
setattr(de, "ist_unmittelbare_Voraussetzung_für_Schritt", OBO.RO_0002090)
setattr(de, "beginnt_mit", OBO.RO_0002224)
setattr(OBO, "starts_with", OBO.RO_0002224)
setattr(de, "endet_mit", OBO.RO_0002230)
setattr(OBO, "ends_with", OBO.RO_0002230)
setattr(OBO, "has_input", OBO.RO_0002233)
setattr(de, "hat_Input", OBO.RO_0002233)
setattr(OBO, "has_output", OBO.RO_0002234)
setattr(de, "hat_Output", OBO.RO_0002234)
setattr(de, "Input_von", OBO.RO_0002352)
setattr(OBO, "input_of", OBO.RO_0002352)
setattr(de, "Output_von", OBO.RO_0002353)
setattr(OBO, "output_of", OBO.RO_0002353)

setattr(OBO, "de", de)