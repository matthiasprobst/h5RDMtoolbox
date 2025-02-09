import pathlib
from typing import Union

import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import URIRef, Literal, Namespace
from rdflib.namespace import RDF


def get_ld(hdf_filename: Union[str, pathlib.Path]) -> rdflib.Graph:
    # Define namespaces
    HDF = Namespace(str(HDF5))

    graph = rdflib.Graph()
    graph.bind("hdf", HDF)

    def add_attributes(node, attrs):
        for key, value in attrs.items():
            attr_uri = rdflib.BNode()
            graph.add((node, HDF[key], Literal(value)))

    def process_group(name, obj):
        group_uri = URIRef(f"{HDF}{name}")
        graph.add((group_uri, RDF.type, HDF.Group))
        add_attributes(group_uri, obj.attrs)

    def process_dataset(name, obj):
        dataset_uri = rdflib.BNode(name)
        graph.add((dataset_uri, RDF.type, HDF.Dataset))
        add_attributes(dataset_uri, obj.attrs)

    with h5py.File(hdf_filename, 'r') as hdf_file:
        root_uri = rdflib.BNode(f"{str(hdf_file.id.id)}")
        graph.add((root_uri, RDF.type, HDF.File))
        root_group = rdflib.BNode(f"{hdf_file['/'].id.id}")
        graph.add((root_uri, HDF5.rootGroup, root_group))
        add_attributes(root_group, hdf_file.attrs)

        hdf_file.visititems(
            lambda name, obj: process_group(name, obj) if isinstance(obj, h5py.Group) else process_dataset(name, obj))

    return graph


if __name__ == "__main__":
    # Example usage
    import h5rdmtoolbox as h5tbx

    with h5tbx.File() as h5:
        h5.attrs["example"] = "example"
        h5.create_dataset("a/b/ds", data=[[1, 2], [3, 4]], chunks=(1, 2))
    hdf_filename = str(h5.hdf_filename)
    g = get_ld(hdf_filename)
    print(g.serialize(format="turtle"))
