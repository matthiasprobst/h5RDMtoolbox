from typing import Optional

import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace
from rdflib import RDF

from h5rdmtoolbox.ld.hdf.attributes import process_attribute
from h5rdmtoolbox.ld.hdf.datasets import process_dataset
from h5rdmtoolbox.ld.utils import get_obj_bnode

HDF = Namespace(str(HDF5))


def process_group(group, graph, parent_uri, blank_node_iri_base: Optional[str] = None, skipND: int = 1):
    """Recursively process HDF5 groups and datasets, adding them to the RDF graph."""
    group_uri = get_obj_bnode(group, blank_node_iri_base=blank_node_iri_base)
    graph.add((group_uri, RDF.type, HDF.Group))
    graph.add((group_uri, HDF.name, rdflib.Literal(group.name, datatype=rdflib.XSD.string)))

    # Iterate through items in the group
    for name, item in group.items():
        item_uri = get_obj_bnode(item, blank_node_iri_base=blank_node_iri_base)
        graph.add((group_uri, HDF.member, item_uri))

        if isinstance(item, h5py.Group):
            process_group(item, graph, group_uri, blank_node_iri_base=blank_node_iri_base)
        elif isinstance(item, h5py.Dataset):
            process_dataset(item, graph, group_uri, item_uri, blank_node_iri_base=blank_node_iri_base, skipND=skipND)

    # Process attributes of the group
    for attr, value in group.attrs.items():
        process_attribute(attr, value, graph, group_uri)
