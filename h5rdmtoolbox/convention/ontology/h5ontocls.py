from typing import List, Union
from typing import Literal

from ontolutils import Thing, namespaces, urirefs

from .h5namespace import HDF5


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
