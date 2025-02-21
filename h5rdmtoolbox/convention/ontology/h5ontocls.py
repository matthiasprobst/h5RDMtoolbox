from typing import List, Union

from ontolutils import Thing, namespaces, urirefs
from ontolutils.namespacelib.hdf5 import HDF5
from pydantic import HttpUrl, NonNegativeInt
from pydantic import field_validator, Field


@namespaces(hdf5=str(HDF5))
@urirefs(Attribute='hdf5:Attribute',
         name='hdf5:name',
         data='hdf5:data')
class Attribute(Thing):
    """HDF5 Attribute"""
    name: str
    data: Union[int, float, List, str, bool]


@namespaces(hdf5=str(HDF5))
@urirefs(attribute='hdf5:attribute',
         NamedObject='hdf5:NamedObject')
class NamedObject(Thing):
    """Abstract class for File, Dataset and Group. Don't use directly."""
    attribute: List[Attribute] = None


@namespaces(hdf5=str(HDF5))
@urirefs(TypeClass='hdf5:TypeClass')
class TypeClass(Thing):
    """HDF5 TypeClass"""
    pass


@namespaces(hdf5=str(HDF5))
@urirefs(Datatype='hdf5:Datatype',
         typeClass='hdf5:typeClass')
class Datatype(Thing):
    """HDF5 Datatype"""
    typeClass: TypeClass = Field(default=None, alias="type_class")

    @field_validator('typeClass', mode='before')
    @classmethod
    def _typeClass(cls, typeClass):
        if isinstance(typeClass, str):
            dt = HttpUrl(typeClass)
            return TypeClass(id=dt)
        return typeClass


@namespaces(hdf5=str(HDF5))
@urirefs(Dimension='hdf5:Dimension',
         dimensionIndex='hdf5:dimensionIndex',
         size='hdf5:size')
class Dimension(Thing):
    dimensionIndex: int = Field(default=None, ge=0, le=31, alias='dimension_index')  # 0..31
    size: NonNegativeInt = Field(default=None, alias='size')


@namespaces(hdf5=str(HDF5))
@urirefs(DataspaceDimension='hdf5:DataspaceDimension',
         currentSize='hdf5:currentSize',
         initialSize='hdf5:initialSize',
         maximumSize='hdf5:maximumSize')
class DataspaceDimension(Dimension):
    """HDF5 Dataspace Dimension"""
    currentSize: int = Field(default=None, alias='current_size', ge=0)
    initialSize: int = Field(default=None, alias='initial_size', ge=0)
    maximumSize: int = Field(default=None, alias='maximum_size', ge=-1)


@namespaces(hdf5=str(HDF5))
@urirefs(ChunkDimension='hdf5:ChunkDimension')
class ChunkDimension(Dimension):
    """HDF5 Chunk Dimension"""
    pass

@namespaces(hdf5=str(HDF5))
@urirefs(ArrayDimension='hdf5:ArrayDimension')
class ArrayDimension(Dimension):
    """HDF5 Array Dimension"""
    pass


@namespaces(hdf5=str(HDF5))
@urirefs(Dataspace='hdf5:Dataspace',
         dimension='hdf5:dimension',
         rank='hdf5:rank')
class Dataspace(Thing):
    """HDF5 Dataspace"""
    dimension: List[DataspaceDimension] = Field(default=None, alias='dimension', max_length=32)  # max 32!
    rank: int = Field(default=None, alias='rank', ge=0, le=32)  # 0..32  rank=ndim


@namespaces(hdf5=str(HDF5))
@urirefs(Dataset='hdf5:Dataset',
         size='hdf5:size',
         name='hdf5:name',
         value='hdf5:value',
         datatype='hdf5:datatype')
class Dataset(NamedObject):
    """A multi-dimensional array"""
    name: str
    size: int
    datatype: Union[HttpUrl, Datatype] = None
    value: Union[int, float, List, str, bool] = None
    rank: int = Field(default=None, alias='rank')
    dataspace: Dataspace = Field(default=None, alias='dataspace')

    @field_validator('datatype', mode='before')
    @classmethod
    def _datatype(cls, datatype):
        if isinstance(datatype, str):
            dt = HttpUrl(datatype)
            return Datatype(id=dt)
        return datatype


@namespaces(hdf5=str(HDF5))
@urirefs(Group='hdf5:Group',
         member='hdf5:member',
         name='hdf5:name')
class Group(NamedObject):
    """HDF5 Group"""
    name: str
    member: List[Union["Group", Dataset]] = None


@namespaces(hdf5=str(HDF5))
@urirefs(File='hdf5:File',
         rootGroup='hdf5:rootGroup')
class File(Thing):
    """HDF5 File"""
    rootGroup: Group
