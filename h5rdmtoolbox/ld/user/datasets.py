import rdflib

from h5rdmtoolbox.ld.user.attributes import process_attribute
from h5rdmtoolbox.ld.utils import get_obj_bnode
from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES
from ..rdf import RDFManager

def process_dataset(dataset, graph, blank_node_iri_base=None):
    dataset_uri = get_obj_bnode(dataset, blank_node_iri_base=blank_node_iri_base)
    for ak, av in dataset.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(dataset, ak, av, graph, blank_node_iri_base=blank_node_iri_base)

    rdf_type = RDFManager(dataset.attrs).type
    if rdf_type is not None:
        graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))
