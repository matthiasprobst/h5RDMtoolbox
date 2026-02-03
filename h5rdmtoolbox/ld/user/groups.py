from typing import Optional

import h5py
import numpy as np
import rdflib
from ontolutils.namespacelib import SCHEMA

from h5rdmtoolbox.ld.rdf import PROTECTED_ATTRIBUTE_NAMES
from h5rdmtoolbox.ld.user.attributes import process_attribute
from h5rdmtoolbox.ld.user.datasets import process_dataset
from h5rdmtoolbox.ld.utils import get_obj_bnode, get_file_bnode
from .utils import apply_rdf_mappings, bnode_from_string
from .utils import to_uriref
from ..rdf import RDFManager


def process_group(*, group, graph, rdf_mappings, blank_node_iri_base: Optional[str] = None):
    group_uri = get_obj_bnode(group, blank_node_iri_base)

    for ak, av in group.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(group, ak, av, graph, blank_node_iri_base)
    apply_rdf_mappings(group, group_uri, graph, rdf_mappings)

    rdf_manager = RDFManager(group.attrs)

    parent_rdf_manager = RDFManager(group.parent.attrs) if group.parent is not None else None
    rdf_type = rdf_manager.type
    rdf_subject = rdf_manager.subject

    # if rdf_predicate:
    #     _predicates = group.attrs.get("RDF_PREDICATE", None)
    #     if _predicates:
    #         self_predicate = json.loads(_predicates).get("SELF", None)
    #         if self_predicate:
    #             parent_uri = get_obj_bnode(group.parent, blank_node_iri_base=blank_node_iri_base)
    #             _parent_subject = RDFManager(group.parent.attrs).subject
    #
    #             if _parent_subject:
    #                 if rdf_subject:
    #                     graph.add((rdflib.URIRef(_parent_subject), rdflib.URIRef(self_predicate), rdflib.URIRef(rdf_subject)))
    #                 else:
    #                     graph.add((rdflib.URIRef(_parent_subject), rdflib.URIRef(self_predicate), group_uri))
    #             else:
    #                 if rdf_subject:
    #                     graph.add((parent_uri, rdflib.URIRef(self_predicate), rdflib.URIRef(rdf_subject)))
    #                 else:
    #                     graph.add((parent_uri, rdflib.URIRef(self_predicate), group_uri))

    if rdf_type is not None and not rdf_subject:
        rdf_subject = bnode_from_string(group.name, blank_node_iri_base=blank_node_iri_base)

    if rdf_type is not None:
        if rdf_subject:
            if isinstance(rdf_type, (list, np.ndarray)):
                for t in rdf_type:
                    graph.add((to_uriref(rdf_subject, blank_node_iri_base), rdflib.RDF.type, to_uriref(t, blank_node_iri_base)))
            else:
                graph.add((to_uriref(rdf_subject, blank_node_iri_base), rdflib.RDF.type, to_uriref(rdf_type, blank_node_iri_base)))
        else:
            if isinstance(rdf_type, (list, np.ndarray)):
                for t in rdf_type:
                    graph.add((group_uri, rdflib.RDF.type, to_uriref(t, blank_node_iri_base)))
            else:
                graph.add((group_uri, rdflib.RDF.type, to_uriref(rdf_type, blank_node_iri_base)))

    if rdf_subject:
        rdf_subject = to_uriref(rdf_subject, blank_node_iri_base)
        graph.add((group_uri, SCHEMA.about, rdf_subject))
        rdf_predicate = rdf_manager.predicate
        if rdf_predicate.get("SELF", None):
            # graph.add((group_uri, rdflib.URIRef(rdf_predicate["SELF"]), rdf_subject))
            if parent_rdf_manager.subject is not None:
                _parent_subject = to_uriref(parent_rdf_manager.subject)
            else:
                _parent_type = parent_rdf_manager.type
                if _parent_type is None:
                    _parent_subject = None
                else:
                    _parent_subject = bnode_from_string(group.parent.name, blank_node_iri_base=blank_node_iri_base)
            if _parent_subject is not None:
                graph.add(
                    (
                        _parent_subject,
                        rdflib.URIRef(rdf_predicate["SELF"]),
                        rdf_subject
                    )
                )

        rdf_file_predicate = rdf_manager.file_predicate
        if rdf_file_predicate is not None:
            file_uri = get_file_bnode(group.file, blank_node_iri_base)
            graph.add(
                (
                    file_uri,
                    rdflib.URIRef(rdf_file_predicate),
                    rdf_subject
                )
            )

    # Iterate through items in the group
    for name, sub_group_or_dataset in group.items():

        # sub_group_or_dataset_uri = rdflib.BNode(sub_group_or_dataset.id.id)
        # graph.add((group_uri, HDF.member, sub_group_or_dataset_uri))

        if isinstance(sub_group_or_dataset, h5py.Group):
            process_group(group=sub_group_or_dataset, graph=graph, rdf_mappings=rdf_mappings,
                          blank_node_iri_base=blank_node_iri_base)

        elif isinstance(sub_group_or_dataset, h5py.Dataset):
            process_dataset(dataset=sub_group_or_dataset, graph=graph, rdf_mappings=rdf_mappings,
                            blank_node_iri_base=blank_node_iri_base)
