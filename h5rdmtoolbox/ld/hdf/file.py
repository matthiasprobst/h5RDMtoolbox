from typing import Optional
from typing import Union

import h5py
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph, RDF
from rdflib import Namespace

from .groups import process_group
from ..rdf import FileRDFManager
from ..utils import optimize_context, get_obj_bnode, get_file_bnode

HDF = Namespace(str(HDF5))


def get_ld(source: Union[str, h5py.File], blank_node_iri_base: Optional[str] = None,
           skipND: int = 1) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""

    if not isinstance(source, h5py.File):
        with h5py.File(source) as h5f:
            return get_ld(h5f, blank_node_iri_base=blank_node_iri_base, skipND=skipND)

    graph = Graph()
    graph.bind("hdf", HDF)

    file_frdf_manager = FileRDFManager(source.attrs)
    if file_frdf_manager.subject:
        file_uri = rdflib.URIRef(file_frdf_manager.subject)
    else:
        file_uri = get_file_bnode(source, blank_node_iri_base=blank_node_iri_base)

    graph.add((file_uri, RDF.type, HDF.File))

    root_group_uri = get_obj_bnode(source["/"], blank_node_iri_base=blank_node_iri_base)
    graph.add((file_uri, HDF5.rootGroup, root_group_uri))

    process_group(source["/"], graph, file_uri, blank_node_iri_base=blank_node_iri_base, skipND=skipND)

    return graph


def get_serialized_ld(
        source,
        blank_node_iri_base,
        format,
        context=None,
        skipND: int = 1
) -> str:
    graph = get_ld(source, blank_node_iri_base, skipND=skipND)
    context = optimize_context(graph, context)
    return graph.serialize(format=format, indent=2, auto_compact=True, context=context)
