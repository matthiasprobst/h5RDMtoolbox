import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace, Literal
from rdflib import RDF

from h5rdmtoolbox.wrapper.ld.attributes import process_attribute
from h5rdmtoolbox.wrapper.ld.datasets import process_dataset

HDF = Namespace(str(HDF5))


def process_group(group, graph, parent_uri):
    """Recursively process HDF5 groups and datasets, adding them to the RDF graph."""
    group_uri = rdflib.BNode(group.id.id)
    graph.add((group_uri, RDF.type, HDF.Group))

    # Iterate through items in the group
    for name, item in group.items():
        item_uri = rdflib.BNode(item.id.id)
        graph.add((group_uri, HDF.member, item_uri))

        if isinstance(item, h5py.Group):
            process_group(item, graph, group_uri)
        elif isinstance(item, h5py.Dataset):
            process_dataset(item, graph, group_uri, item_uri)

    # Process attributes of the group
    for attr, value in group.attrs.items():
        if group.rdf.predicate[attr]:
            if group.rdf.object[attr]:
                graph.add((group_uri, rdflib.URIRef(group.rdf.predicate[attr]), rdflib.URIRef(group.rdf.object[attr])))
            else:
                graph.add((group_uri, rdflib.URIRef(group.rdf.predicate[attr]), Literal(value)))
        process_attribute(attr, value, graph, group_uri)
