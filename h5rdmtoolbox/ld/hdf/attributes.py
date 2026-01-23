import warnings

import numpy as np
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace, Literal, XSD, RDF

from ..utils import get_attr_node, to_literal

HDF = Namespace(str(HDF5))


def process_attribute(*, name, value, graph, parent, parent_uri, blank_node_iri_base):
    """Process an HDF5 attribute, adding it to the RDF graph."""
    if name.isupper() or name.startswith('@'):
        return
    attr_uri = get_attr_node(
        parent,
        name,
        blank_node_iri_base
    )

    if isinstance(value, str):
        graph.add((attr_uri, RDF.type, HDF5.StringAttribute))
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='ignore')
        graph.add((attr_uri, HDF.data, to_literal(value)))
    elif isinstance(value, int):
        graph.add((attr_uri, RDF.type, HDF5.IntegerAttribute))
        graph.add((attr_uri, HDF.data, Literal(value, datatype=XSD.integer)))
    elif isinstance(value, float):
        graph.add((attr_uri, RDF.type, HDF5.FloatAttribute))
        graph.add((attr_uri, HDF.data, Literal(value, datatype=XSD.float)))
    elif isinstance(value, np.ndarray):
        if value.ndim == 1:
            for v in value:
                graph.add((attr_uri, HDF.data, to_literal(v)))
            if value.dtype.kind in {'i', 'u'}:
                graph.add((attr_uri, RDF.type, HDF5.IntegerAttribute))
            elif value.dtype.kind == 'f':
                graph.add((attr_uri, RDF.type, HDF5.FloatAttribute))
            else:
                graph.add((attr_uri, RDF.type, HDF5.Attribute))
        else:
            warnings.warn(f"Attribute data containing more than one dimension is not fully supported.")
            graph.add((attr_uri, RDF.type, HDF5.Attribute))
            graph.add((attr_uri, HDF.data, to_literal(value)))
    else:
        # attributes that are string bytes should be HDF5.StringAttribute
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='ignore')
            graph.add((attr_uri, RDF.type, HDF5.StringAttribute))
        else:
            graph.add((attr_uri, RDF.type, HDF5.Attribute))
        graph.add((attr_uri, HDF.data, to_literal(value)))

    graph.add((attr_uri, HDF.name, Literal(name)))
    graph.add((parent_uri, HDF.attribute, attr_uri))
