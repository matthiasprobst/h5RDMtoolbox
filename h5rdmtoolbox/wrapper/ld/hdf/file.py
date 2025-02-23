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


def get_ld(source: Union[str, h5tbx.File], blank_node_iri_base: Optional[str] = None,
           skipND: int = 1) -> rdflib.Graph:
    """Convert an HDF5 file into an RDF graph."""

    if not isinstance(source, h5tbx.File):
        with h5tbx.File(source) as h5f:
            return get_ld(h5f, blank_node_iri_base=blank_node_iri_base, skipND=skipND)

    graph = Graph()
    graph.bind("hdf", HDF)

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


if __name__ == "__main__":
    import h5rdmtoolbox as h5tbx
    from rdflib import FOAF
    from ontolutils import M4I

    with h5tbx.File() as h5:
        g = h5.create_group("contact")
        g.attrs["name"] = "Probst"
        g.attrs["id"] = "0000-0001-8729-0482"

        # enrich with RDF metadata:
        g.rdf.type = FOAF.Person
        g.rdf.subject = "https://orcid.org/0000-0001-8729-0482"
        g.rdf.predicate["name"] = FOAF.lastName
        g.rdf.predicate["id"] = M4I.orcidId

        ttl = h5.serialize(structural=False, fmt="ttl")
    print(ttl)
