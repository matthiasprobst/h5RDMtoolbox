from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef

from typing import Literal


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


from ontolutils import Thing, namespaces, urirefs
from typing import List, Union


@namespaces(hdf5=HDF5._NS)
@urirefs(Attribute='hdf5:Attribute',
         name='hdf5:name',
         value='hdf5:value')
class Attribute(Thing):
    """HDF5 Attribute"""
    name: str
    value: Union[int, float, List, str, bool]


@namespaces(hdf5=HDF5._NS)
@urirefs(attribute='hdf5:attribute')
class _HDF5Thing(Thing):
    """Abstract class for File, Dataset and Group. Dont use directly."""
    attribute: List[Attribute] = None


Datatype = Literal[
    'H5T_INTEGER',
    'H5T_FLOAT',
    'H5T_STRING',
]


@namespaces(hdf5=HDF5._NS)
@urirefs(Dataset='hdf5:Dataset',
         size='hdf5:size',
         name='hdf5:name',
         value='hdf5:value',
         datatype='hdf5:datatype')
class Dataset(_HDF5Thing):
    """A multi-dimensional array"""
    name: str
    size: int
    datatype: Datatype = None
    value: Union[int, float, List, str, bool] = None


@namespaces(hdf5=HDF5._NS)
@urirefs(Group='hdf5:Group',
         member='hdf5:member',
         name='hdf5:name')
class Group(_HDF5Thing):
    """HDF5 Group"""
    name: str
    member: List[Union["Group", Dataset]] = None


@namespaces(hdf5=HDF5._NS)
@urirefs(File='hdf5:File',
         rootGroup='hdf5:rootGroup')
class File(Thing):
    """HDF5 File"""
    rootGroup: Group
