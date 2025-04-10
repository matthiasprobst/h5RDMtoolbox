from typing import Optional
from typing import Union

import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph
from rdflib import Namespace

from h5rdmtoolbox.ld.user.attributes import process_file_attribute
from h5rdmtoolbox.ld.user.groups import process_group
from h5rdmtoolbox.ld.utils import get_file_bnode
from ..rdf import FileRDFManager

HDF = Namespace(str(HDF5))


def get_ld(source: Union[str, h5py.File], blank_node_iri_base: Optional[str] = None) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""

    if not isinstance(source, h5py.File):
        with h5py.File(source) as h5f:
            return get_ld(h5f)

    graph = Graph()
    graph.bind("m4i", rdflib.URIRef("http://w3id.org/nfdi4ing/metadata4ing#"))
    graph.bind("ssno", rdflib.URIRef("https://matthiasprobst.github.io/ssno#"))
    graph.bind("piv", rdflib.URIRef("https://matthiasprobst.github.io/pivmeta#"))

    file_frdf_manager = FileRDFManager(source.attrs)

    if file_frdf_manager.subject:
        file_uri = rdflib.URIRef(file_frdf_manager.subject)
    else:
        file_uri = get_file_bnode(source, blank_node_iri_base=blank_node_iri_base)


    if source.name == "/":
        file_rdf = file_frdf_manager.type
    else:
        file_rdf = None


    if file_rdf:
        if isinstance(file_rdf, list):
            for rdf_type in file_rdf:
                graph.add((file_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))
        else:
            graph.add((file_uri, rdflib.RDF.type, rdflib.URIRef(file_rdf)))

    for ak, av in source.attrs.items():
        process_file_attribute(source, ak, av, graph, blank_node_iri_base, file_uri)

    process_group(source, graph, blank_node_iri_base=blank_node_iri_base)

    return graph
