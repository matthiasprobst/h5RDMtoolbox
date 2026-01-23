import json
import re
import warnings
from typing import Union

import numpy as np
from dateutil import parser
from ontolutils import SCHEMA
from ontolutils.classes.thing import is_url
from rdflib import RDF, DCTERMS, XSD, URIRef, Literal, Graph, BNode

from h5rdmtoolbox.ld.utils import get_attr_dtype_as_xsd, get_obj_bnode, to_literal
from .utils import to_uriref
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
    # reject version-like strings composed only of digits and dots, e.g. "2.5.3"
    if re.match(r"^\d+(?:\.\d+)+$", value):
        return None
    try:
        dt = parser.parse(value)
        # reject implausible years (versions can parse as year 2, etc.)
        if dt.year < 1000:
            return None
        # Prüfe, ob nur ein Datum (YYYY-MM-DD) vorliegt
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return dt.date().isoformat(), XSD.date
        else:
            return dt.isoformat(), XSD.dateTime
    except (ValueError, OverflowError):
        return None


def process_file_attribute(parent_obj, name, data, graph, file_uri: Union[URIRef, BNode], blank_node_iri_base):
    rdf_user_type = FileRDFManager(parent_obj.attrs).type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((file_uri, RDF.type, to_uriref(t, blank_node_iri_base)))
        else:
            graph.add((file_uri, RDF.type, to_uriref(rdf_user_type, blank_node_iri_base)))
    rdf_user_predicate = FileRDFManager(parent_obj.attrs).predicate[name]

    rdf_user_object = FileRDFManager(parent_obj.attrs).object[name]
    if rdf_user_object and not rdf_user_predicate:
        if isinstance(rdf_user_object, (Literal, str, int, float)) and not str(rdf_user_object).startswith(
                "http"):
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_LITERAL_OBJECTS
        else:
            rdf_user_predicate = FALLBACK_PREDICATE_FOR_IRI_OBJECTS
        # rdf_user_object = SCHEMA.PropertyValue

    if rdf_user_predicate:
        if rdf_user_object:
            if isinstance(rdf_user_object, Literal):
                graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base), rdf_user_object))
            if isinstance(rdf_user_object, str) and rdf_user_object.startswith('http'):
                graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                           to_uriref(rdf_user_object, blank_node_iri_base)))
            elif isinstance(rdf_user_object, list):
                for ruo in rdf_user_object:
                    if isinstance(ruo, Literal):
                        graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base), ruo))

                    elif isinstance(ruo, str) and ruo.startswith('http'):
                        graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base), URIRef(ruo)))

                    elif isinstance(ruo, dict):
                        try:
                            obj_graph = Graph().parse(data=json.loads(json.dumps(ruo)), format="json-ld")
                            # relate the obj_graph with the predicate:
                            _subjects = set(obj_graph.subjects())
                            if len(_subjects) != 1:
                                warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                                              f"Expected exactly one subject, found {len(_subjects)}")
                            obj_graph.add(
                                (file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                 to_uriref(list(_subjects)[0], blank_node_iri_base)))
                            graph += obj_graph
                        except Exception as e:
                            warnings.warn(
                                f"Error parsing JSON-LD object for attribute. name={name}, data={data}. Orig. Error: {e}")

            elif isinstance(rdf_user_object, dict):
                try:
                    jsonld_dict = json.loads(json.dumps(rdf_user_object))
                    obj_graph = Graph().parse(data=jsonld_dict,
                                              format="json-ld")

                    if "@graph" not in jsonld_dict:
                        use_subject = jsonld_dict.get("@id")
                        obj_graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                       to_uriref(use_subject, blank_node_iri_base)))
                    else:
                        _graph_entities = jsonld_dict["@graph"]
                        if len(_graph_entities) == 1:
                            use_subject = _graph_entities[0].get("@id")
                            obj_graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                           to_uriref(use_subject, blank_node_iri_base)))
                        else:
                            for _entity in _graph_entities:
                                if RDF.type in _entity and _entity[RDF.type] == str(SCHEMA.PropertyValue):
                                    use_subject = _entity.get("@id")
                                    obj_graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                                   to_uriref(use_subject, blank_node_iri_base)))

                    # obj_graph = Graph().parse(data=json.loads(json.dumps(rdf_user_object)), format="json-ld")
                    # # relate the obj_graph with the predicate:
                    # _subjects = set(obj_graph.subjects())
                    # if len(_subjects) != 1:
                    #     warnings.warn(f"Error parsing JSON-LD object for attribute. name={name}, data={data}. "
                    #                   f"Expected exactly one subject, found {len(_subjects)}")
                    # obj_graph.add((file_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                    #                to_uriref(list(_subjects)[0], blank_node_iri_base)))
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
                     to_uriref(rdf_user_predicate, blank_node_iri_base),
                     Literal(date_value, datatype=xsd_type))
                )
            elif is_url(data):
                graph.add(
                    (file_uri,
                     to_uriref(rdf_user_predicate, blank_node_iri_base),
                     URIRef(data))
                )
            else:
                graph.add(
                    (file_uri,
                     to_uriref(rdf_user_predicate, blank_node_iri_base),
                     Literal(data, datatype=get_attr_dtype_as_xsd(data)))
                )
    return graph


def process_attribute(parent_obj, name, data, graph, blank_node_iri_base):
    rdf_manager = RDFManager(parent_obj.attrs)

    parent_uri = rdf_manager.subject
    if parent_uri:
        parent_uri = to_uriref(parent_uri, blank_node_iri_base)
    else:
        parent_uri = get_obj_bnode(parent_obj, blank_node_iri_base)
    rdf_user_type = rdf_manager.type
    if rdf_user_type is not None:
        if isinstance(rdf_user_type, (list, np.ndarray)):
            for t in rdf_user_type:
                graph.add((parent_uri, RDF.type, to_uriref(t, blank_node_iri_base)))
        else:
            graph.add((parent_uri, RDF.type, to_uriref(rdf_user_type, blank_node_iri_base)))
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
                _graph.add((parent_uri, to_uriref(rdf_user_predicate, blank_node_iri_base), _rdf_user_object))
            elif isinstance(_rdf_user_object, str) and _rdf_user_object.startswith('http'):
                _graph.add((parent_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                            to_uriref(_rdf_user_object, blank_node_iri_base)))
            elif isinstance(_rdf_user_object, list):
                for _itm in _rdf_user_object:
                    _graph = _add_to_graph(_itm, _graph)
            else:
                if isinstance(_rdf_user_object, dict):
                    try:
                        jsonld_dict = json.loads(json.dumps(_rdf_user_object))
                        obj_graph = Graph().parse(data=jsonld_dict,
                                                  format="json-ld")

                        if "@graph" not in jsonld_dict:
                            use_subject = jsonld_dict.get("@id")
                            obj_graph.add((parent_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                           to_uriref(use_subject, blank_node_iri_base)))
                        else:
                            _graph_entities = jsonld_dict["@graph"]
                            if len(_graph_entities) == 1:
                                use_subject = _graph_entities[0].get("@id")
                                obj_graph.add((parent_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                               to_uriref(use_subject, blank_node_iri_base)))
                            else:
                                for _entity in _graph_entities:
                                    if RDF.type in _entity and _entity[RDF.type] == str(SCHEMA.PropertyValue):
                                        use_subject = _entity.get("@id")
                                        obj_graph.add((parent_uri, to_uriref(rdf_user_predicate, blank_node_iri_base),
                                                       to_uriref(use_subject, blank_node_iri_base)))

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
                     to_uriref(rdf_user_predicate, blank_node_iri_base),
                     Literal(date_value, datatype=xsd_type))
                )
            elif is_url(data):
                graph.add(
                    (parent_uri,
                     to_uriref(rdf_user_predicate, blank_node_iri_base),
                     URIRef(data))
                )
            else:
                graph.add(
                    (
                        parent_uri,
                        to_uriref(rdf_user_predicate, blank_node_iri_base),
                        to_literal(data)
                    )  # Literal(data, datatype=get_attr_dtype_as_xsd(data)))
                )
        return _graph

    if rdf_user_predicate:
        graph = _add_to_graph(rdf_user_object, graph)
    return graph
