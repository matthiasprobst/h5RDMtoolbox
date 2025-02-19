from typing import Optional
from typing import Union

import rdflib
from ontolutils.namespacelib import M4I
from ontolutils.namespacelib import SCHEMA
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph
from rdflib import Namespace

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper.ld.user.attributes import process_file_attribute
from h5rdmtoolbox.wrapper.ld.user.groups import process_group
from h5rdmtoolbox.wrapper.ld.utils import get_file_bnode

HDF = Namespace(str(HDF5))


def get_ld(source: Union[str, h5tbx.File], blank_node_iri_base: Optional[str] = None) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""

    if not isinstance(source, h5tbx.File):
        with h5tbx.File(source) as h5f:
            return get_ld(h5f)

    graph = Graph()

    file_uri = get_file_bnode(source, blank_node_iri_base=blank_node_iri_base)
    file_rdf = source.frdf.type

    if file_rdf:
        if isinstance(file_rdf, list):
            for rdf_type in file_rdf:
                graph.add((file_uri, rdflib.RDF.type, rdflib.URIRef(rdf_type)))
        else:
            graph.add((file_uri, rdflib.RDF.type, rdflib.URIRef(file_rdf)))

    for ak, av in source.attrs.items():
        process_file_attribute(source, ak, av, graph, blank_node_iri_base)

    process_group(source, graph, blank_node_iri_base=blank_node_iri_base)

    return graph


if __name__ == "__main__":
    import h5rdmtoolbox as h5tbx

    with h5tbx.File() as h5:
        h5.attrs["version", SCHEMA.version] = "1.2.3"

        ds = h5.create_dataset("a/b/ds", data=[[1, 2], [3, 4]], chunks=(1, 2), compression="gzip", compression_opts=2)
        ds2 = h5.create_dataset("nochunk", data=[[1, 2], [3, 4]], chunks=None)
        ds.rdf.type = M4I.NumericalVariable

    graph = get_ld(str(h5.hdf_filename))
    print(graph.serialize(format="turtle"))
