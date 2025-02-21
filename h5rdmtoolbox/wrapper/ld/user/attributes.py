import json
import warnings

import rdflib
from rdflib import RDF

from h5rdmtoolbox.wrapper.ld.utils import get_attr_dtype_as_XSD, get_obj_bnode


def process_file_attribute(parent_obj, name, data, graph, blank_node_iri_base):
    parent_uri = get_obj_bnode(parent_obj, blank_node_iri_base)
    rdf_user_type = parent_obj.frdf.type
    if rdf_user_type:
        graph.add((parent_uri, RDF.type, rdflib.URIRef(rdf_user_type)))
    rdf_user_predicate = parent_obj.frdf.predicate[name]

    if rdf_user_predicate:
        rdf_user_object = parent_obj.frdf.object[name]
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


def process_attribute(parent_obj, name, data, graph, blank_node_iri_base):
    parent_uri = parent_obj.rdf.subject
    if parent_uri:
        parent_uri = rdflib.URIRef(parent_uri)
    else:
        parent_uri = get_obj_bnode(parent_obj, blank_node_iri_base)
    rdf_user_type = parent_obj.rdf.type
    if rdf_user_type:
        graph.add((parent_uri, RDF.type, rdflib.URIRef(rdf_user_type)))
    rdf_user_predicate = parent_obj.rdf.predicate[name]

    if rdf_user_predicate:
        rdf_user_object = parent_obj.rdf.object[name]
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
