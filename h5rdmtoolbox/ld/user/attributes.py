import json
import re
import warnings
from typing import Union

import numpy as np
from dateutil import parser
from ontolutils import SCHEMA
from ontolutils.classes.thing import is_url
from rdflib import RDF, DCTERMS, XSD, URIRef, Literal, Graph, BNode

from h5rdmtoolbox.ld.utils import get_attr_dtype_as_xsd, get_obj_bnode
from ..rdf import FileRDFManager, RDFManager

# FALLBACK_PREDICATE = SCHEMA.additionalProperty
FALLBACK_PREDICATE_FOR_LITERAL_OBJECTS = RDF.value
FALLBACK_PREDICATE_FOR_IRI_OBJECTS = DCTERMS.relation


def _is_date_str(value: str):
    """Returns a tuple of (date_string, xsd_type) if the value is a date string, else None."""
    if not isinstance(value, str):
        return None
    # quick check, that first character is a digit
    if not re.match(r"^\d", value):
        return None
    try:
        dt = parser.parse(value)
        # Prüfe, ob nur ein Datum (YYYY-MM-DD) vorliegt
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return dt.date().isoformat(), XSD.date
        else:
            return dt.isoformat(), XSD.dateTime
    except (ValueError, OverflowError):
        return None


def process_file_attribute(parent_obj, name, data, graph, file_uri: Union[URIRef, BNode]):
    rdf_user_type = FileRDFManager(parent_obj.attrs).type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((file_uri, RDF.type, URIRef(t)))
        else:
            graph.add((file_uri, RDF.type, URIRef(rdf_user_type)))
    rdf_user_predicate = FileRDFManager(parent_obj.attrs).predicate[name]

    rdf_user_object = FileRDFManager(parent_obj.attrs).object[name]
    if rdf_user_object and not rdf_user_predicate:
        if isinstance(rdf_user_object, (Literal, str, int, float)) and not str(rdf_user_object).startswith(
                "http"):
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_LITERAL_OBJECTS
        else:
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_IRI_OBJECTS
        rdf_user_object = SCHEMA.PropertyValue

    if rdf_user_predicate:
        if rdf_user_object:
            if isinstance(rdf_user_object, Literal):
                graph.add((file_uri, URIRef(rdf_user_predicate), rdf_user_object))
            if isinstance(rdf_user_object, str) and rdf_user_object.startswith('http'):
                graph.add((file_uri, URIRef(rdf_user_predicate), URIRef(rdf_user_object)))
            elif isinstance(rdf_user_object, list):
                for ruo in rdf_user_object:
                    if isinstance(ruo, Literal):
                        graph.add((file_uri, URIRef(rdf_user_predicate), ruo))

                    elif isinstance(ruo, str) and ruo.startswith('http'):
                        graph.add((file_uri, URIRef(rdf_user_predicate), URIRef(ruo)))

                    elif isinstance(ruo, dict):
                        try:
                            obj_graph = Graph().parse(data=json.loads(json.dumps(ruo)), format="json-ld")
                            # relate the obj_graph with the predicate:
                            _subjects = set(obj_graph.subjects())
                            if len(_subjects) != 1:
                                warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                              f"Expected exactly one subject, found {len(_subjects)}")
                            obj_graph.add((file_uri, URIRef(rdf_user_predicate), list(_subjects)[0]))
                            graph += obj_graph
                        except Exception as e:
                            warnings.warn(
                                f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")

            elif isinstance(rdf_user_object, dict):
                try:
                    obj_graph = Graph().parse(data=json.loads(json.dumps(rdf_user_object)), format="json-ld")
                    # relate the obj_graph with the predicate:
                    _subjects = set(obj_graph.subjects())
                    if len(_subjects) != 1:
                        warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                      f"Expected exactly one subject, found {len(_subjects)}")
                    obj_graph.add((file_uri, URIRef(rdf_user_predicate), list(_subjects)[0]))
                    graph += obj_graph
                except Exception as e:
                    warnings.warn(
                        f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")
        else:
            date_info = _is_date_str(data)
            if date_info:
                date_value, xsd_type = date_info
                graph.add(
                    (file_uri,
                     URIRef(rdf_user_predicate),
                     Literal(date_value, datatype=xsd_type))
                )
            elif is_url(data):
                graph.add(
                    (file_uri,
                     URIRef(rdf_user_predicate),
                     URIRef(data))
                )
            else:
                graph.add(
                    (file_uri,
                     URIRef(rdf_user_predicate),
                     Literal(data, datatype=get_attr_dtype_as_xsd(data)))
                )
    return graph


def process_attribute(parent_obj, name, data, graph, blank_node_iri_base):
    rdf_manager = RDFManager(parent_obj.attrs)

    parent_uri = rdf_manager.subject
    if parent_uri:
        parent_uri = URIRef(parent_uri)
    else:
        parent_uri = get_obj_bnode(parent_obj, blank_node_iri_base)
    rdf_user_type = rdf_manager.type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((parent_uri, RDF.type, URIRef(t)))
        else:
            graph.add((parent_uri, RDF.type, URIRef(rdf_user_type)))
    rdf_user_predicate = rdf_manager.predicate[name]
    rdf_user_object = rdf_manager.object[name]
    if rdf_user_object and not rdf_user_predicate:
        if isinstance(rdf_user_object, (Literal, str, int, float)) and not str(rdf_user_object).startswith(
                "http"):
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_LITERAL_OBJECTS
        else:
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_IRI_OBJECTS

    def _add_to_graph(_rdf_user_object, _graph):
        if _rdf_user_object:
            if isinstance(_rdf_user_object, Literal):
                _graph.add((parent_uri, URIRef(rdf_user_predicate), _rdf_user_object))
            elif isinstance(_rdf_user_object, str) and _rdf_user_object.startswith('http'):
                _graph.add((parent_uri, URIRef(rdf_user_predicate), URIRef(_rdf_user_object)))
            elif isinstance(_rdf_user_object, list):
                for _itm in _rdf_user_object:
                    _graph = _add_to_graph(_itm, _graph)
            else:
                if isinstance(_rdf_user_object, dict):
                    try:
                        obj_graph = Graph().parse(data=json.loads(json.dumps(_rdf_user_object)),
                                                  format="json-ld")
                        # relate the obj_graph with the predicate:
                        _subjects = set(obj_graph.subjects())
                        if len(_subjects) != 1:
                            warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                          f"Expected exactly one subject, found {len(_subjects)}")
                        obj_graph.add((parent_uri, URIRef(rdf_user_predicate), list(_subjects)[0]))
                        _graph += obj_graph
                    except Exception as e:
                        warnings.warn(
                            f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")
        else:
            date_info = _is_date_str(data)
            if date_info:
                date_value, xsd_type = date_info
                graph.add(
                    (parent_uri,
                     URIRef(rdf_user_predicate),
                     Literal(date_value, datatype=xsd_type))
                )
            elif is_url(data):
                graph.add(
                    (parent_uri,
                     URIRef(rdf_user_predicate),
                     URIRef(data))
                )
            else:
                graph.add(
                    (parent_uri,
                     URIRef(rdf_user_predicate),
                     Literal(data, datatype=get_attr_dtype_as_xsd(data)))
                )
        return _graph

    if rdf_user_predicate:
        graph = _add_to_graph(rdf_user_object, graph)
    return graph
