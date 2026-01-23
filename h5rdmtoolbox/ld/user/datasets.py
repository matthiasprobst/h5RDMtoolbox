import rdflib
from ontolutils.namespacelib import SCHEMA

from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES
from h5rdmtoolbox.ld.user.attributes import process_attribute
from h5rdmtoolbox.ld.utils import get_obj_bnode
from ..rdf import RDFManager


def process_dataset(*, dataset, graph, rdf_mappings, blank_node_iri_base=None):
    dataset_uri = get_obj_bnode(dataset, blank_node_iri_base=blank_node_iri_base)
    for ak, av in dataset.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(dataset, ak, av, graph, blank_node_iri_base=blank_node_iri_base)
            if ak in rdf_mappings:
                mapping = rdf_mappings[ak]
                predicate_uri = rdflib.URIRef(mapping['predicate'])
                if predicate_uri:
                    object_uri = mapping.get('object')
                    if object_uri:
                        if callable(object_uri):
                            object_uri = str(object_uri(av))
                            if object_uri is None:
                                continue
                        graph.add((dataset_uri, predicate_uri, rdflib.URIRef(object_uri)))
                    else:
                        graph.add((dataset_uri, predicate_uri, rdflib.Literal(av)))
                type_uri = mapping.get('type')
                if type_uri:
                    graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(type_uri)))

    rdf_type = RDFManager(dataset.attrs).type
    if rdf_type is not None:
        graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))

    rdf_subject = RDFManager(dataset.attrs).subject
    if rdf_subject:
        graph.add((dataset_uri, SCHEMA.about, rdflib.URIRef(rdf_subject)))
