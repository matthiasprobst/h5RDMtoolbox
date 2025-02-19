import rdflib

from h5rdmtoolbox.wrapper.ld.user.attributes import process_attribute
from h5rdmtoolbox.wrapper.ld.utils import get_obj_bnode
from h5rdmtoolbox.wrapper.rdf import PROTECTED_ATTRIBUTE_NAMES


def process_dataset(dataset, graph, blank_node_iri_base=None):
    dataset_uri = get_obj_bnode(dataset, blank_node_iri_base=blank_node_iri_base)
    for ak, av in dataset.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(dataset, ak, av, graph, blank_node_iri_base=blank_node_iri_base)

    rdf_type = dataset.rdf.type
    if rdf_type:
        graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))
