from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef


class HDF5(DefinedNamespace):
    # uri = "http://purl.allotrope.org/ontologies/hdf5/1.8#"
    # Manually created, therefore is incomplete!!! Only basic definitions were taken.
    # Date: 2024-03-18
    _fail = True
    ArrayDatatype: URIRef
    ArrayDimension: URIRef
    ArrayValue: URIRef
    AtomicDatatype: URIRef
    attribute: URIRef
    Attribute: URIRef
    chunk: URIRef
    Chunk: URIRef
    Coordinate: URIRef
    coordinate: URIRef
    coordinateIndex: URIRef
    count: URIRef
    data: URIRef
    dataSource: URIRef
    Dataset: URIRef
    datatype: URIRef
    Datatype: URIRef
    dimension: URIRef
    Dimension: URIRef
    dimensionIndex: URIRef
    DimensionIndexType: URIRef
    File: URIRef  # synonyms HDF5 file. A container for storing grouped collections of multi-dimensional arrays containing scientific data following the HDF 5 specification.
    Group: URIRef
    member: URIRef
    name: URIRef
    NamedObject: URIRef
    rootGroup: URIRef  # Relation between the HDF file and its root group.
    size: URIRef  # synonyms: size of datatype, size of dimension
    value: URIRef

    _NS = Namespace("http://purl.allotrope.org/ontologies/hdf5/1.8#")
