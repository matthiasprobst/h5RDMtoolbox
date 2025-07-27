import hashlib
import os
import pathlib
from dataclasses import dataclass
from typing import Optional
from typing import Union

import h5py
import rdflib
from rdflib.namespace import XSD

from .globals import _CACHE


def get_attr_dtype_as_XSD(data):
    if isinstance(data, str):
        return XSD.string
    if isinstance(data, int):
        return XSD.integer
    if isinstance(data, float):
        return XSD.float
    return None


def optimize_context(graph, context=None):
    bound_namespaces = {k: str(v) for k, v in graph.namespaces()}
    bound_namespaces["m4i"] = "http://w3id.org/nfdi4ing/metadata4ing#"

    # Collect actually used namespaces
    selected_namespaces = dict()

    for s, p, o in graph:  # Iterate through triples
        for term in (s, p, o):
            if isinstance(term, rdflib.URIRef):
                for k, v in selected_namespaces.items():
                    if v in term:
                        break
                for k, v in bound_namespaces.items():
                    if v in term:
                        selected_namespaces[k] = v
                        break

    context = context or {}
    selected_namespaces.update(context)
    return selected_namespaces


def _get_obj_id(file_id: float, obj: Union[h5py.Dataset, h5py.Group], name: Optional[str] = None):
    if name:
        name = f"/{name}"
    _file_id = _get_file_id(obj.file)
    return hashlib.md5(f"{_file_id}/{obj.name}{name}".encode()).hexdigest()
    # return hashlib.md5(f"{obj.file.id.id}/{obj.name}{name}".encode()).hexdigest()


def _get_attr_id(obj: Union[h5py.Dataset, h5py.Group], name: str):
    if not isinstance(name, str):
        raise ValueError("Attribute name must be a string")
    return hashlib.md5(f"{obj.file.id.id}/{obj.name}/attr/{name}".encode()).hexdigest()


def _get_file_id(file: h5py.File):
    """deterministic ID for the file based on its name and modification time."""
    if isinstance(file, (str, pathlib.Path)):
        filename = str(file)
    elif isinstance(file, h5py.File):
        filename = file.filename
    else:
        raise ValueError("Expected h5py.File object or file path as string or pathlib.Path")
    if filename in _CACHE["FILE_MTIME_ID"]:
        return _CACHE["FILE_MTIME_ID"][filename]
    _id = os.path.getmtime(file.filename)
    _CACHE["FILE_MTIME_ID"][filename] = _id
    return _id


def get_file_bnode(file: h5py.File,
                   blank_node_iri_base: Optional[str]):
    if not isinstance(file, h5py.File):
        raise ValueError("Expected h5py.File object")
    _id = _get_file_id(file)
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_obj_bnode(obj: Union[h5py.Dataset, h5py.Group], blank_node_iri_base):
    file_id = _get_file_id(obj.file)
    _id = _get_obj_id(file_id, obj)
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_attr_bnode(obj: Union[h5py.Dataset, h5py.Group],
                   name: str,
                   blank_node_iri_base: Optional[str]):
    _file_id = _get_file_id(obj.file)
    _id = hashlib.md5(f"{_file_id}/{obj.name}/attr/{name}".encode()).hexdigest()
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(f"{_id}")


@dataclass()
class ExtractionOptions:
    structural: bool
    semantic: bool
