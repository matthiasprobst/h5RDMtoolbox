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

HDF = Namespace(str(HDF5))


def get_ld(
        source: Union[str, h5py.File],
        file_uri: Optional[str] = None,
        rdf_mappings: Dict[str, RDFMappingEntry] = None
) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""
    if rdf_mappings is None:
        rdf_mappings = {}
    if not isinstance(source, h5py.File):
        with h5py.File(source) as h5f:
            return get_ld(h5f, file_uri=file_uri)

    graph = Graph()
    graph.bind("m4i", to_uriref("http://w3id.org/nfdi4ing/metadata4ing#"))
    graph.bind("ssno", to_uriref("https://matthiasprobst.github.io/ssno#"))
    graph.bind("piv", to_uriref("https://matthiasprobst.github.io/pivmeta#"))

    file_frdf_manager = FileRDFManager(source.attrs)

    if file_frdf_manager.subject:
        file_node = to_uriref(file_frdf_manager.subject)
    else:
        file_node = get_file_bnode(source, file_uri=file_uri)

    if source.name == "/":
        file_rdf_type = file_frdf_manager.type
    else:
        file_rdf_type = None

    if file_rdf_type is not None:
        if isinstance(file_rdf_type, list) or isinstance(file_rdf_type, np.ndarray):
            for rdf_type in file_rdf_type:
                graph.add((file_node, rdflib.RDF.type, to_uriref(rdf_type, file_uri)))
        else:
            graph.add((file_node, rdflib.RDF.type, to_uriref(file_rdf_type, file_uri)))

    for ak, av in source.attrs.items():
        process_file_attribute(source, ak, av, graph, file_node, blank_node_iri_base=file_uri)
        if ak in rdf_mappings:
            mapping = rdf_mappings[ak]
            predicate = to_uriref(mapping.get("predicate"), file_uri)
            if predicate is not None:
                graph.add((file_node, predicate, rdflib.Literal(av)))

    process_group(group=source, graph=graph, blank_node_iri_base=file_uri, rdf_mappings=rdf_mappings)

    return graph
