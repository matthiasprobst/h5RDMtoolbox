import pathlib
from typing import Optional
from typing import Protocol

from .hdfdb import FileDB
from .hdfdb import FilesDB, ObjDB
from .interface import HDF5DBInterface


def find(source, *args, **kwargs):
    if isinstance(source, (str, pathlib.Path)):
        return FileDB(source).find(*args, **kwargs)
    elif isinstance(source, (list, tuple)):
        return FilesDB(source).find(*args, **kwargs)
    return ObjDB(source).find(*args, **kwargs)


def find_one(source, *args, **kwargs):
    if isinstance(source, (str, pathlib.Path)):
        return FileDB(source).find_one(*args, **kwargs)
    elif isinstance(source, (list, tuple)):
        return FilesDB(source).find_one(*args, **kwargs)
    else:
        return ObjDB(source).find_one(*args, **kwargs)


class RDFQuerySource(Protocol):
    def rdf(self, *args, **kwargs):
        pass


def rdf_find(source, *,
             rdf_subject: Optional[str] = None,
             rdf_type: Optional[str] = None,
             rdf_predicate: Optional[str] = None,
             rdf_object: Optional[str] = None,
             recursive: bool = True):
    """Find function for RDF triples

    Parameters
    ----------
    source: Union[str, pathlib.Path, h5tbx.Group]
        Filename or hdf group
    rdf_subject: Optional[str]
        The RDF subject to search for if provided
    rdf_type: Optional[str]
        The RDF type to search for if provided
    rdf_predicate: Optional[str]
        The RDF predicate to search for if provided
    rdf_object: Optional[str]
        The RDF object to search for if provided
    recursive: bool=True
        If True, search recursively. If False, only search the current group
    """
    if isinstance(source, (str, pathlib.Path)):
        return FileDB(source).rdf_find(rdf_subject=rdf_subject,
                                       rdf_type=rdf_type,
                                       rdf_predicate=rdf_predicate,
                                       rdf_object=rdf_object,
                                       recursive=recursive)
    elif isinstance(source, (list, tuple)):
        return FilesDB(source).rdf_find(rdf_subject=rdf_subject,
                                        rdf_type=rdf_type,
                                        rdf_predicate=rdf_predicate,
                                        rdf_object=rdf_object,
                                        recursive=recursive)
    else:
        return ObjDB(source).rdf_find(rdf_subject=rdf_subject,
                                      rdf_type=rdf_type,
                                      rdf_predicate=rdf_predicate,
                                      rdf_object=rdf_object,
                                      recursive=recursive)


__all__ = ['FileDB', 'FilesDB', 'ObjDB', 'HDF5DBInterface', 'lazy']
