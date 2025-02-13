import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace

from h5rdmtoolbox.wrapper.ld.user.attributes import process_attribute
from h5rdmtoolbox.wrapper.ld.utils import get_obj_bnode
from h5rdmtoolbox.wrapper.rdf import PROTECTED_ATTRIBUTE_NAMES

HDF = Namespace(str(HDF5))


def process_dataset(dataset, graph):
    dataset_uri = get_obj_bnode(dataset)
    for ak, av in dataset.attrs.items():
        if ak not in PROTECTED_ATTRIBUTE_NAMES:
            process_attribute(dataset, ak, av, graph)

    rdf_type = dataset.rdf.type
    if rdf_type:
        graph.add((dataset_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))
