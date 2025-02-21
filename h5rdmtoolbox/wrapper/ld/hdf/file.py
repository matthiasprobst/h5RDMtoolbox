from typing import Optional
from typing import Union

import rdflib
from ontolutils.namespacelib import M4I
from ontolutils.namespacelib import SCHEMA
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph, RDF
from rdflib import Namespace

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper.ld.hdf.groups import process_group
from h5rdmtoolbox.wrapper.ld.utils import optimize_context, get_obj_bnode, get_file_bnode

HDF = Namespace(str(HDF5))


def get_ld(source: Union[str, h5tbx.File], blank_node_iri_base:Optional[str]=None) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""

    if not isinstance(source, h5tbx.File):
        with h5tbx.File(source) as h5f:
            return get_ld(h5f, blank_node_iri_base=blank_node_iri_base)

    graph = Graph()
    graph.bind("hdf", HDF)

    file_uri = get_file_bnode(source, blank_node_iri_base=blank_node_iri_base)
    graph.add((file_uri, RDF.type, HDF.File))

    root_group_uri = get_obj_bnode(source["/"], blank_node_iri_base=blank_node_iri_base)
    graph.add((file_uri, HDF5.rootGroup, root_group_uri))

    process_group(source["/"], graph, file_uri, blank_node_iri_base=blank_node_iri_base)

    return graph


def get_serialized_ld(
        source,
        blank_node_iri_base,
        format,
        context=None
) -> str:
    graph = get_ld(source, blank_node_iri_base)
    context = optimize_context(graph, context)
    return graph.serialize(format=format, indent=2, auto_compact=True, context=context)


if __name__ == "__main__":
    import h5rdmtoolbox as h5tbx

    with h5tbx.File() as h5:
        h5.attrs["version", SCHEMA.version] = "1.2.3"

        ds = h5.create_dataset("a/b/ds", data=[[1, 2], [3, 4]], chunks=(1, 2), compression="gzip", compression_opts=2)
        ds2 = h5.create_dataset("nochunk", data=[[1, 2], [3, 4]], chunks=None)
        ds.rdf.type = M4I.NumericalVariable

    graph = get_ld(str(h5.hdf_filename), structural=True, semantic=False)
    print(graph.serialize(format="turtle"))
