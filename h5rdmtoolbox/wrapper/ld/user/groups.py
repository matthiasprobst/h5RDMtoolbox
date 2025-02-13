import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace

from h5rdmtoolbox.wrapper.ld.user.attributes import process_attribute
from h5rdmtoolbox.wrapper.ld.user.datasets import process_dataset
from h5rdmtoolbox.wrapper.ld.utils import get_obj_bnode
from typing import Optional
HDF = Namespace(str(HDF5))


def process_group(group, graph, blank_node_iri_base: Optional[str]=None):
    for ak, av in group.attrs.items():
        process_attribute(group, ak, av, graph, blank_node_iri_base)

    group_uri = get_obj_bnode(group, blank_node_iri_base)
    rdf_type = group.rdf.type
    rdf_subject = group.rdf.subject
    if rdf_type:
        if rdf_subject:
            graph.add((rdflib.URIRef(rdf_subject), rdflib.RDF.type, rdflib.URIRef(rdf_type)))
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
