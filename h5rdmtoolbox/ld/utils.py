import hashlib
from dataclasses import dataclass
from typing import Optional
from typing import Union

import h5py
import rdflib
from rdflib.namespace import XSD


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


def _get_obj_id(obj: Union[h5py.Dataset, h5py.Group], name: Optional[str] = None):
    if name:
        name = f"/{name}"
    return hashlib.md5(f"{obj.file.id.id}/{obj.name}{name}".encode()).hexdigest()


def get_file_bnode(file: h5py.File,
                   blank_node_iri_base: Optional[str]):
    if not isinstance(file, h5py.File):
        raise ValueError("Expected h5py.File object")
    _id = _get_obj_id(file, name="file")
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_obj_bnode(obj: Union[h5py.Dataset, h5py.Group], blank_node_iri_base):
    _id = _get_obj_id(obj)
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_attr_bnode(obj: Union[h5py.Dataset, h5py.Group], name: str, blank_node_iri_base: Optional[str]):
    _id = _get_obj_id(obj, name)
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(f"{_id}_{name}")


@dataclass()
class ExtractionOptions:
    structural: bool
    semantic: bool
