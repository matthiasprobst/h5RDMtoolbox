from typing import Optional

import h5py
import numpy as np
import rdflib
from ontolutils.namespacelib import SCHEMA

from h5rdmtoolbox.ld.user.attributes import process_attribute
from h5rdmtoolbox.ld.user.datasets import process_dataset
from h5rdmtoolbox.ld.utils import get_obj_bnode, get_file_bnode
from ..rdf import RDFManager


def process_group(group, graph, blank_node_iri_base: Optional[str] = None):
    for ak, av in group.attrs.items():
        process_attribute(group, ak, av, graph, blank_node_iri_base)

    group_uri = get_obj_bnode(group, blank_node_iri_base)
    rdf_manager = RDFManager(group.attrs)
    rdf_type = rdf_manager.type
    rdf_subject = rdf_manager.subject

    # if rdf_type is None:
    if rdf_subject:
        graph.add((group_uri, SCHEMA.about, rdflib.URIRef(rdf_subject)))
        rdf_predicate = rdf_manager.predicate
        if rdf_predicate.get("SELF", None):
            graph.add((group_uri, rdflib.URIRef(rdf_predicate["SELF"]), rdflib.URIRef(rdf_subject)))
        rdf_file_predicate = rdf_manager.file_predicate
        if rdf_file_predicate is not None:
            file_uri = get_file_bnode(group.file, blank_node_iri_base)
            graph.add((file_uri, rdflib.URIRef(rdf_file_predicate), rdflib.URIRef(rdf_subject)))
    if rdf_type is not None:
        if rdf_subject:
            if isinstance(rdf_type, (list, np.ndarray)):
                for t in rdf_type:
                    graph.add((rdflib.URIRef(rdf_subject), rdflib.RDF.type, rdflib.URIRef(t)))
            else:
                graph.add((rdflib.URIRef(rdf_subject), rdflib.RDF.type, rdflib.URIRef(rdf_type)))
        else:
            if isinstance(rdf_type, (list, np.ndarray)):
                for t in rdf_type:
                    graph.add((group_uri, rdflib.RDF.type, rdflib.URIRef(t)))
            else:
                graph.add((group_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))

    # Iterate through items in the group
    for name, sub_group_or_dataset in group.items():

        # sub_group_or_dataset_uri = rdflib.BNode(sub_group_or_dataset.id.id)
        # graph.add((group_uri, HDF.member, sub_group_or_dataset_uri))

        if isinstance(sub_group_or_dataset, h5py.Group):
            process_group(sub_group_or_dataset, graph, blank_node_iri_base=blank_node_iri_base)

        elif isinstance(sub_group_or_dataset, h5py.Dataset):
            process_dataset(sub_group_or_dataset, graph, blank_node_iri_base=blank_node_iri_base)
