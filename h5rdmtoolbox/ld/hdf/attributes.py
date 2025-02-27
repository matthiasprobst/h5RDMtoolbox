import rdflib
from ontolutils.namespacelib.hdf5 import HDF5
from rdflib import Namespace, Literal
from rdflib import XSD, RDF

HDF = Namespace(str(HDF5))


def process_attribute(name, value, graph, parent_uri):
    """Process an HDF5 attribute, adding it to the RDF graph."""
    if name.isupper() or name.startswith('@'):
        return
    attr_uri = rdflib.BNode()

    if isinstance(value, str):
        graph.add((attr_uri, RDF.type, HDF5.StringAttribute))
        graph.add((attr_uri, HDF.data, Literal(value, datatype=XSD.string)))
    elif isinstance(value, int):
        graph.add((attr_uri, RDF.type, HDF5.IntegerAttribute))
        graph.add((attr_uri, HDF.data, Literal(value, datatype=XSD.integer)))
    elif isinstance(value, float):
        graph.add((attr_uri, RDF.type, HDF5.FloatAttribute))
        graph.add((attr_uri, HDF.data, Literal(value, datatype=XSD.float)))
    else:
        graph.add((attr_uri, RDF.type, HDF5.Attribute))
        graph.add((attr_uri, HDF.data, Literal(value)))

    graph.add((attr_uri, HDF.name, rdflib.Literal(name)))
    graph.add((parent_uri, HDF.attribute, attr_uri))
