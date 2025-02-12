from typing import Union

import rdflib
from ontolutils.namespacelib import M4I
from ontolutils.namespacelib import SCHEMA
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Graph, RDF
from rdflib import Namespace

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper.ld.groups import process_group

HDF = Namespace(str(HDF5))


def get_ld(source: Union[str, h5tbx.File]):
    """Convert an HDF5 file into an RDF graph."""
    if not isinstance(source, h5tbx.File):
        with h5tbx.File(source) as h5:
            return get_ld(h5)
    graph = Graph()
    graph.bind("hdf", HDF)

    root_uri = rdflib.BNode(source.id.id)
    graph.add((root_uri, RDF.type, HDF.File))
    process_group(source, graph, root_uri)

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
