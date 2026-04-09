from typing import Optional, Dict
from typing import Union

import h5py
import numpy as np
import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph
from rdflib import Namespace

from h5rdmtoolbox.ld.user.attributes import process_file_attribute
from h5rdmtoolbox.ld.user.groups import process_group
from h5rdmtoolbox.ld.utils import get_file_bnode
from .utils import to_uriref
from .._types import RDFMappingEntry
from ..rdf import FileRDFManager
from .utils import apply_rdf_mappings

HDF = Namespace(str(HDF5))


def _bind_default_namespaces(graph: Graph) -> None:
    graph.bind("m4i", to_uriref("http://w3id.org/nfdi4ing/metadata4ing#"))
    graph.bind("ssno", to_uriref("https://matthiasprobst.github.io/ssno#"))
    graph.bind("piv", to_uriref("https://matthiasprobst.github.io/pivmeta#"))


def _get_file_node(h5_file: h5py.File, file_uri: Optional[str]):
    file_rdf_manager = FileRDFManager(h5_file.attrs)
    if file_rdf_manager.subject:
        return to_uriref(file_rdf_manager.subject)
    return get_file_bnode(h5_file, file_uri=file_uri)


def _add_file_rdf_types(h5_file: h5py.File, file_node, graph: Graph, file_uri: Optional[str]) -> None:
    file_rdf_type = FileRDFManager(h5_file.attrs).type if h5_file.name == "/" else None
    if file_rdf_type is None:
        return

    if isinstance(file_rdf_type, (list, np.ndarray)):
        for rdf_type in file_rdf_type:
            graph.add((file_node, rdflib.RDF.type, to_uriref(rdf_type, file_uri)))
        return

    graph.add((file_node, rdflib.RDF.type, to_uriref(file_rdf_type, file_uri)))


def _build_graph_from_file(
        h5_file: h5py.File,
        *,
        file_uri: Optional[str],
        rdf_mappings: Optional[Dict[str, RDFMappingEntry]],
) -> rdflib.Graph:
    mappings = rdf_mappings or {}
    graph = Graph()
    _bind_default_namespaces(graph)

    file_node = _get_file_node(h5_file, file_uri=file_uri)
    _add_file_rdf_types(h5_file, file_node, graph, file_uri)

    for attr_name, attr_value in h5_file.attrs.items():
        process_file_attribute(
            h5_file,
            attr_name,
            attr_value,
            graph,
            file_node,
            blank_node_iri_base=file_uri,
        )

    apply_rdf_mappings(h5_file, file_node, graph, mappings)
    process_group(
        group=h5_file,
        graph=graph,
        blank_node_iri_base=file_uri,
        rdf_mappings=mappings,
    )
    return graph


def get_ld(
        source: Union[str, h5py.File],
        file_uri: Optional[str] = None,
        rdf_mappings: Dict[str, RDFMappingEntry] = None
) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""
    if isinstance(source, h5py.File):
        return _build_graph_from_file(source, file_uri=file_uri, rdf_mappings=rdf_mappings)

    # Keep historical behavior for path input: rdf_mappings is not forwarded.
    with h5py.File(source) as h5_file:
        return _build_graph_from_file(h5_file, file_uri=file_uri, rdf_mappings=None)
