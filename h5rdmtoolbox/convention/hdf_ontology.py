# from typing import List, Union
# from typing import Literal
# from ontolutils.namespacelib.hdf5 import HDF5
# from ontolutils import Thing, namespaces, urirefs
#
# _HDF5_NS_IRI = str(HDF5)
#
# @namespaces(hdf5=_HDF5_NS_IRI)
# @urirefs(Attribute='hdf5:Attribute',
#          name='hdf5:name',
#          value='hdf5:value')
# class Attribute(Thing):
#     """HDF5 Attribute"""
#     name: str
#     value: Union[int, float, List, str, bool]
#
#
# @namespaces(hdf5=_HDF5_NS_IRI)
# @urirefs(attribute='hdf5:attribute')
# class NamedObject(Thing):
#     """Abstract class for File, Dataset and Group. Don't use directly."""
#     attribute: List[Attribute] = None
#
#
# Datatype = Literal[
#     'H5T_INTEGER',
#     'H5T_FLOAT',
#     'H5T_STRING',
# ]
#
#
# @namespaces(hdf5=_HDF5_NS_IRI)
# @urirefs(Dataset='hdf5:Dataset',
#          size='hdf5:size',
#          name='hdf5:name',
#          value='hdf5:value',
#          datatype='hdf5:datatype')
# class Dataset(NamedObject):
#     """A multi-dimensional array"""
#     name: str
#     size: int
#     datatype: Datatype = None
#     value: Union[int, float, List, str, bool] = None
#
#
# @namespaces(hdf5=_HDF5_NS_IRI)
# @urirefs(Group='hdf5:Group',
#          member='hdf5:member',
#          name='hdf5:name')
# class Group(NamedObject):
#     """HDF5 Group"""
#     name: str
#     member: List[Union["Group", Dataset]] = None
#
#
# @namespaces(hdf5=_HDF5_NS_IRI)
# @urirefs(File='hdf5:File',
#          rootGroup='hdf5:rootGroup')
# class File(Thing):
#     """HDF5 File"""
#     rootGroup: Group
