import json
import warnings

import numpy as np
import rdflib
from rdflib import RDF, DCTERMS

from h5rdmtoolbox.ld.utils import get_attr_dtype_as_XSD, get_obj_bnode
from ..rdf import FileRDFManager, RDFManager


def process_file_attribute(parent_obj, name, data, graph, blank_node_iri_base, file_uri):
    rdf_user_type = FileRDFManager(parent_obj.attrs).type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((file_uri, RDF.type, rdflib.URIRef(t)))
        else:
            graph.add((file_uri, RDF.type, rdflib.URIRef(rdf_user_type)))
    rdf_user_predicate = FileRDFManager(parent_obj.attrs).predicate[name]

    rdf_user_object = FileRDFManager(parent_obj.attrs).object[name]
    if rdf_user_object and not rdf_user_predicate:
        rdf_user_predicate = DCTERMS.relation

    if rdf_user_predicate:
        if rdf_user_object:
            if isinstance(rdf_user_object, str) and rdf_user_object.startswith('http'):
                graph.add((file_uri, rdflib.URIRef(rdf_user_predicate), rdflib.URIRef(rdf_user_object)))
            elif isinstance(rdf_user_object, list):
                for ruo in rdf_user_object:

                    if isinstance(ruo, str) and ruo.startswith('http'):
                        graph.add((file_uri, rdflib.URIRef(rdf_user_predicate), rdflib.URIRef(ruo)))

                    elif isinstance(ruo, dict):
                        try:
                            obj_graph = rdflib.Graph().parse(data=json.loads(json.dumps(ruo)), format="json-ld")
                            # relate the obj_graph with the predicate:
                            _subjects = set(obj_graph.subjects())
                            if len(_subjects) != 1:
                                warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                              f"Expected exactly one subject, found {len(_subjects)}")
                            obj_graph.add((file_uri, rdflib.URIRef(rdf_user_predicate), list(_subjects)[0]))
                            graph += obj_graph
                        except Exception as e:
                            warnings.warn(
                                f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")

            elif isinstance(rdf_user_object, dict):
                    try:
                        obj_graph = rdflib.Graph().parse(data=json.loads(json.dumps(rdf_user_object)), format="json-ld")
                        # relate the obj_graph with the predicate:
                        _subjects = set(obj_graph.subjects())
                        if len(_subjects) != 1:
                            warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                          f"Expected exactly one subject, found {len(_subjects)}")
                        obj_graph.add((file_uri, rdflib.URIRef(rdf_user_predicate), list(_subjects)[0]))
                        graph += obj_graph
                    except Exception as e:
                        warnings.warn(
                            f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")
        else:
            graph.add(
                (file_uri,
                 rdflib.URIRef(rdf_user_predicate),
                 rdflib.Literal(data, datatype=get_attr_dtype_as_XSD(data)))
            )
    return graph


def process_attribute(parent_obj, name, data, graph, blank_node_iri_base):

    rdf_manager = RDFManager(parent_obj.attrs)

    parent_uri = rdf_manager.subject
    if parent_uri:
        parent_uri = rdflib.URIRef(parent_uri)
    else:
        parent_uri = get_obj_bnode(parent_obj, blank_node_iri_base)
    rdf_user_type = rdf_manager.type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((parent_uri, RDF.type, rdflib.URIRef(t)))
        else:
            graph.add((parent_uri, RDF.type, rdflib.URIRef(rdf_user_type)))
    rdf_user_predicate = rdf_manager.predicate[name]
    rdf_user_object = rdf_manager.object[name]
    if rdf_user_object and not rdf_user_predicate:
        rdf_user_predicate = DCTERMS.relation

    if rdf_user_predicate:
        if rdf_user_object:
            if isinstance(rdf_user_object, str) and rdf_user_object.startswith('http'):
                graph.add((parent_uri, rdflib.URIRef(rdf_user_predicate), rdflib.URIRef(rdf_user_object)))
            else:
                if isinstance(rdf_user_object, dict):
                    try:
                        obj_graph = rdflib.Graph().parse(data=json.loads(json.dumps(rdf_user_object)), format="json-ld")
                        # relate the obj_graph with the predicate:
                        _subjects = set(obj_graph.subjects())
                        if len(_subjects) != 1:
                            warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                          f"Expected exactly one subject, found {len(_subjects)}")
                        obj_graph.add((parent_uri, rdflib.URIRef(rdf_user_predicate), list(_subjects)[0]))
                        graph += obj_graph
                    except Exception as e:
                        warnings.warn(
                            f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")
        else:
            graph.add(
                (parent_uri,
                 rdflib.URIRef(rdf_user_predicate),
                 rdflib.Literal(data, datatype=get_attr_dtype_as_XSD(data)))
            )
    return graph
