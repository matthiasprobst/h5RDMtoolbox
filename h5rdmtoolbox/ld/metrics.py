"""Knowledge graph metrics for RDF extracted from HDF5 files."""

import pathlib
import re
from typing import Dict, Optional, Union

import rdflib

from . import get_ld

STANDARD_PREFIXES = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcterms": "http://purl.org/dc/terms/",
    "doi": "https://doi.org/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prof": "http://www.w3.org/ns/dx/prof/",
    "prov": "http://www.w3.org/ns/prov#",
    "qudt": "http://qudt.org/schema/qudt/",
    "quantitykind": "http://qudt.org/vocab/quantitykind/",
    "schema": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ssno": "https://matthiasprobst.github.io/ssno#",
    "unit": "http://qudt.org/vocab/unit/",
    "zenodo": "https://zenodo.org/records/",
    "zenodo_record": "https://zenodo.org/record/",
}


def bind_standard_prefixes(graph: rdflib.Graph) -> None:
    """Bind common namespaces without replacing prefixes already defined by the graph."""
    for prefix, namespace in STANDARD_PREFIXES.items():
        graph.bind(prefix, rdflib.Namespace(namespace), override=False, replace=False)


def graph_label(value, rdf_graph: Optional[rdflib.Graph] = None) -> str:
    """Return a compact display label for an RDF term."""
    if isinstance(value, rdflib.URIRef):
        namespace_manager = rdf_graph.namespace_manager if rdf_graph is not None else rdflib.Graph().namespace_manager
        text = str(value)
        try:
            normalized = str(namespace_manager.normalizeUri(value))
            if not normalized.startswith("<") and not re.match(r"^ns\d+:", normalized):
                return normalized
        except Exception:
            pass
        for prefix, namespace in STANDARD_PREFIXES.items():
            if text.startswith(namespace) and text != namespace:
                return f"{prefix}:{text[len(namespace):]}"
        try:
            return namespace_manager.qname(value)
        except Exception:
            pass
        if rdf_graph is not None:
            namespaces = sorted(
                ((prefix, str(namespace)) for prefix, namespace in rdf_graph.namespaces() if prefix),
                key=lambda item: len(item[1]),
                reverse=True,
            )
            for prefix, namespace in namespaces:
                if text.startswith(namespace) and text != namespace:
                    return f"{prefix}:{text[len(namespace):]}"
        return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text
    text = str(value)
    return text if len(text) <= 48 else f"{text[:45]}..."


def _percent(numerator: int, denominator: int) -> float:
    return (numerator / denominator * 100.0) if denominator else 0.0


def _external_namespace(value) -> str:
    text = str(value)
    if "#" in text:
        return text.rsplit("#", 1)[0] + "#"
    if "/" in text:
        return text.rsplit("/", 1)[0] + "/"
    return text


def _resource_terms(subject, predicate, obj) -> list:
    return [
        term
        for term in (subject, predicate, obj)
        if isinstance(term, (rdflib.URIRef, rdflib.BNode))
    ]


def compute_graph_metrics(rdf_graph: rdflib.Graph, base_namespace: Optional[str] = None) -> Dict[str, object]:
    """Compute RDF knowledge graph metrics for an existing graph."""
    bind_standard_prefixes(rdf_graph)
    triples = list(rdf_graph)
    subjects = set()
    objects = set()
    predicates = set()
    iris = set()
    blank_nodes = set()
    resource_nodes = set()
    literal_count = 0
    untyped_literal_count = 0
    empty_literal_count = 0
    predicate_counts = {}
    subject_triple_counts = {}
    class_instances = {}
    datatype_counts = {}
    language_counts = {}
    labels = set()
    typed_subjects = set()
    same_as_count = 0
    external_iri_counts = {}
    out_degree = {}
    in_degree = {}
    adjacency = {}

    for subject, predicate, obj in triples:
        subjects.add(subject)
        predicates.add(predicate)
        objects.add(obj)
        subject_triple_counts[subject] = subject_triple_counts.get(subject, 0) + 1

        for term in _resource_terms(subject, predicate, obj):
            if isinstance(term, rdflib.URIRef):
                iris.add(term)
                namespace = _external_namespace(term)
                if not base_namespace or not str(term).startswith(base_namespace):
                    external_iri_counts[namespace] = external_iri_counts.get(namespace, 0) + 1
            elif isinstance(term, rdflib.BNode):
                blank_nodes.add(term)

        predicate_label = graph_label(predicate, rdf_graph)
        predicate_counts[predicate_label] = predicate_counts.get(predicate_label, 0) + 1

        if predicate == rdflib.RDF.type:
            typed_subjects.add(subject)
            class_label = graph_label(obj, rdf_graph)
            class_instances.setdefault(class_label, set()).add(subject)

        if predicate == rdflib.RDFS.label:
            labels.add(subject)

        if predicate == rdflib.OWL.sameAs:
            same_as_count += 1

        resource_nodes.add(subject)

        if isinstance(obj, rdflib.Literal):
            literal_count += 1
            datatype_label = graph_label(obj.datatype, rdf_graph) if obj.datatype else "None"
            datatype_counts[datatype_label] = datatype_counts.get(datatype_label, 0) + 1
            language_label = obj.language or "None"
            language_counts[language_label] = language_counts.get(language_label, 0) + 1
            if obj.datatype is None and obj.language is None:
                untyped_literal_count += 1
            if str(obj) == "":
                empty_literal_count += 1
            continue

        resource_nodes.add(obj)
        out_degree[subject] = out_degree.get(subject, 0) + 1
        in_degree[obj] = in_degree.get(obj, 0) + 1
        adjacency.setdefault(subject, set()).add(obj)
        adjacency.setdefault(obj, set()).add(subject)

    seen = set()
    component_sizes = []
    for node in resource_nodes:
        if node in seen:
            continue
        stack = [node]
        seen.add(node)
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for neighbor in adjacency.get(current, set()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        component_sizes.append(size)

    largest_distance = 0
    for start in resource_nodes:
        distances = {start: 0}
        queue = [start]
        for current in queue:
            for neighbor in adjacency.get(current, set()):
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        if distances:
            largest_distance = max(largest_distance, max(distances.values()))

    resource_count = len(resource_nodes)
    subjects_without_type = len(subjects - typed_subjects)
    subjects_with_labels = len(labels)
    subjects_missing_labels = len(subjects - labels)
    duplicate_triples = len(triples) - len(set(triples))
    subjects_with_one_triple = sum(1 for count in subject_triple_counts.values() if count == 1)
    weakly_connected_nodes = sum(
        1 for node in resource_nodes
        if in_degree.get(node, 0) + out_degree.get(node, 0) <= 1
    )
    class_counts = {label: len(instances) for label, instances in class_instances.items()}

    return {
        "triples": len(triples),
        "subjects": len(subjects),
        "predicates": len(predicates),
        "objects": len(objects),
        "iri_count": len(iris),
        "blank_nodes": len(blank_nodes),
        "literals": literal_count,
        "avg_triples_per_subject": len(triples) / len(subjects) if subjects else 0.0,
        "classes": len(class_counts),
        "subjects_without_type": subjects_without_type,
        "resource_nodes": resource_count,
        "avg_out_degree": sum(out_degree.values()) / resource_count if resource_count else 0.0,
        "avg_in_degree": sum(in_degree.values()) / resource_count if resource_count else 0.0,
        "weakly_connected_nodes": weakly_connected_nodes,
        "components": len(component_sizes),
        "largest_component": max(component_sizes, default=0),
        "largest_distance": largest_distance,
        "datatype_distribution": sorted(datatype_counts.items(), key=lambda item: (-item[1], item[0])),
        "language_distribution": sorted(language_counts.items(), key=lambda item: (-item[1], item[0])),
        "untyped_literals": untyped_literal_count,
        "empty_literals": empty_literal_count,
        "subjects_with_labels": subjects_with_labels,
        "subjects_missing_labels": subjects_missing_labels,
        "label_coverage": _percent(subjects_with_labels, len(subjects)),
        "duplicate_triples": duplicate_triples,
        "subjects_with_one_triple": subjects_with_one_triple,
        "blank_node_percentage": _percent(len(blank_nodes), resource_count),
        "same_as_count": same_as_count,
        "external_iri_count": sum(external_iri_counts.values()),
        "top_external_namespaces": sorted(external_iri_counts.items(), key=lambda item: (-item[1], item[0]))[:10],
        "top_predicates": sorted(predicate_counts.items(), key=lambda item: (-item[1], item[0]))[:10],
        "rare_predicates": sorted(predicate_counts.items(), key=lambda item: (item[1], item[0]))[:10],
        "predicate_distribution": sorted(predicate_counts.items(), key=lambda item: (-item[1], item[0])),
        "top_classes": sorted(class_counts.items(), key=lambda item: (-item[1], item[0]))[:10],
        "top_out_degree": [
            (graph_label(node, rdf_graph), count)
            for node, count in sorted(out_degree.items(), key=lambda item: (-item[1], graph_label(item[0], rdf_graph)))[:10]
        ],
        "top_in_degree": [
            (graph_label(node, rdf_graph), count)
            for node, count in sorted(in_degree.items(), key=lambda item: (-item[1], graph_label(item[0], rdf_graph)))[:10]
        ],
    }


def compute_metrics(
        hdf_filename: Union[str, pathlib.Path],
        structural: bool = True,
        contextual: bool = True,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
        context: Optional[Dict] = None,
        rdf_mappings: Optional[Dict] = None,
) -> Dict[str, object]:
    """Compute RDF knowledge graph metrics for an HDF5 file."""
    graph = get_ld(
        hdf_filename,
        structural=structural,
        contextual=contextual,
        file_uri=file_uri,
        skipND=skipND,
        context=context,
        rdf_mappings=rdf_mappings,
    )
    return compute_graph_metrics(graph, base_namespace=file_uri)
