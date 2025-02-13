import hashlib
import pathlib
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


def get_file_bnode(file: h5py.File,
                   blank_node_iri_base: Optional[str]):
    _id = hashlib.md5(str(pathlib.Path(file.filename).absolute()).encode()).hexdigest()
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_obj_bnode(obj: Union[h5py.Dataset, h5py.Group], blank_node_iri_base):
    _id = hashlib.md5(obj.name.encode()).hexdigest()
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}')
    return rdflib.BNode(_id)


def get_attr_bnode(obj: Union[h5py.Dataset, h5py.Group], name: str, blank_node_iri_base: Optional[str]):
    _id = hashlib.md5(obj.name.encode()).hexdigest()
    if blank_node_iri_base:
        return rdflib.URIRef(f'{blank_node_iri_base}{_id}_{name}')
    return rdflib.BNode(f"{_id}_{name}")


@dataclass()
class ExtractionOptions:
    structural: bool
    semantic: bool
