from typing import List, Union

from ontolutils import Thing, namespaces, urirefs
from ontolutils.namespacelib.hdf5 import HDF5
from pydantic import HttpUrl
from pydantic import field_validator, Field


@namespaces(hdf5=str(HDF5))
@urirefs(Attribute='hdf5:Attribute',
         name='hdf5:name',
         value='hdf5:value')
class Attribute(Thing):
    """HDF5 Attribute"""
    name: str
    value: Union[int, float, List, str, bool]


@namespaces(hdf5=str(HDF5))
@urirefs(attribute='hdf5:attribute')
class _HDF5Thing(Thing):
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
@urirefs(Dataset='hdf5:Dataset',
         size='hdf5:size',
         name='hdf5:name',
         value='hdf5:value',
         datatype='hdf5:datatype')
class Dataset(_HDF5Thing):
    """A multi-dimensional array"""
    name: str
    size: int
    datatype: Union[HttpUrl, Datatype] = None
    value: Union[int, float, List, str, bool] = None

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
class Group(_HDF5Thing):
    """HDF5 Group"""
    name: str
    member: List[Union["Group", Dataset]] = None


@namespaces(hdf5=str(HDF5))
@urirefs(File='hdf5:File',
         rootGroup='hdf5:rootGroup')
class File(Thing):
    """HDF5 File"""
    rootGroup: Group
