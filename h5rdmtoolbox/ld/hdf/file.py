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


def _get_file_node(h5_file: h5py.File, file_uri: Optional[str]):
    file_rdf_manager = FileRDFManager(h5_file.attrs)
    if file_rdf_manager.subject:
        return rdflib.URIRef(file_rdf_manager.subject)
    return get_file_bnode(h5_file, file_uri=file_uri)


def _build_graph_from_file(
        h5_file: h5py.File,
        *,
        file_uri: Optional[str],
        skipND: int,
) -> rdflib.Graph:
    graph = Graph()
    graph.bind("hdf", HDF)

    file_node = _get_file_node(h5_file, file_uri=file_uri)
    graph.add((file_node, RDF.type, HDF.File))

    root_group = h5_file["/"]
    root_group_uri = get_obj_bnode(obj=root_group, blank_node_iri_base=file_uri)
    graph.add((file_node, HDF5.rootGroup, root_group_uri))

    process_group(root_group, graph, blank_node_iri_base=file_uri, skipND=skipND)
    return graph


def get_ld(source: Union[str, h5py.File],
           file_uri: Optional[str] = None,
           skipND: int = 1) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""
    if isinstance(source, h5py.File):
        return _build_graph_from_file(source, file_uri=file_uri, skipND=skipND)
    with h5py.File(source) as h5_file:
        return _build_graph_from_file(h5_file, file_uri=file_uri, skipND=skipND)


def get_serialized_ld(
        source,
        blank_node_iri_base,
        format,
        context=None,
        skipND: int = 1
) -> str:
    graph = get_ld(source=source, file_uri=blank_node_iri_base, skipND=skipND)
    context = optimize_context(graph, context)
    return graph.serialize(format=format, indent=2, auto_compact=True, context=context)
