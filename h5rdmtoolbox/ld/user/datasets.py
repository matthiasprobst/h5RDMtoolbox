import rdflib
from ontolutils.namespacelib import SCHEMA

from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES
from h5rdmtoolbox.ld.user.attributes import process_attribute
from h5rdmtoolbox.ld.utils import get_obj_bnode
from .utils import apply_rdf_mappings
from ..rdf import RDFManager
import json

def process_dataset(*, dataset, graph, rdf_mappings, blank_node_iri_base=None):
    dataset_uri = get_obj_bnode(dataset, blank_node_iri_base=blank_node_iri_base)
    for ak, av in dataset.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(dataset, ak, av, graph, blank_node_iri_base=blank_node_iri_base)
        apply_rdf_mappings(dataset, dataset_uri, graph, rdf_mappings)

    rdf_type = RDFManager(dataset.attrs).type
    if rdf_type is not None:
        graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))

    rdf_subject = RDFManager(dataset.attrs).subject
    if rdf_subject:
        graph.add((dataset_uri, SCHEMA.about, rdflib.URIRef(rdf_subject)))

    rdf_predicate = RDFManager(dataset.attrs).predicate
    if rdf_predicate:
        _predicates = dataset.attrs.get("RDF_PREDICATE", None)
        if _predicates:
            self_predicate = json.loads(dataset.attrs["RDF_PREDICATE"]).get("SELF", None)
            if self_predicate:
                parent_uri = get_obj_bnode(dataset.parent, blank_node_iri_base=blank_node_iri_base)

                _parent_subject = RDFManager(dataset.parent.attrs).subject

                if _parent_subject:
                    if rdf_subject:
                        graph.add((rdflib.URIRef(_parent_subject), rdflib.URIRef(self_predicate), rdflib.URIRef(rdf_subject)))
                    else:
                        graph.add((rdflib.URIRef(_parent_subject), rdflib.URIRef(self_predicate), dataset_uri))
                else:
                    if rdf_subject:
                        graph.add((parent_uri, rdflib.URIRef(self_predicate), rdflib.URIRef(rdf_subject)))
                    else:
                        graph.add((parent_uri, rdflib.URIRef(self_predicate), dataset_uri))