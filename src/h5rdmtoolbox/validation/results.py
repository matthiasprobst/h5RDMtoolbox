"""Structured results and HDF5 locations from standard SHACL reports."""

from dataclasses import dataclass
from typing import Optional

import rdflib
from rdflib.namespace import SH

HDF = rdflib.Namespace("http://purl.allotrope.org/ontologies/hdf5/1.8#")


@dataclass(frozen=True)
class Violation:
    """One standard SHACL validation result, with an optional HDF5 location."""

    focus_node: rdflib.term.Node
    property_path: Optional[rdflib.term.Node]
    severity: Optional[rdflib.term.Node]
    messages: tuple[str, ...]
    hdf_path: Optional[str]


@dataclass(frozen=True)
class ValidationResult:
    """Conformance and the complete standard report; execution errors raise."""

    conforms: bool
    results_graph: rdflib.Graph
    results_text: str
    violations: tuple[Violation, ...]

    @property
    def messages(self) -> list[str]:
        """Return all violation messages in report order."""
        return [message for item in self.violations for message in item.messages]

    @property
    def nodes(self) -> list[rdflib.term.Node]:
        """Return the focus node for each violation."""
        return [item.focus_node for item in self.violations]


def _resolve_hdf_path(graph, node):
    name = graph.value(node, HDF.name)
    if name is not None and str(name).startswith('/'):
        return str(name)
    for owner in graph.subjects(HDF.attribute, node):
        owner_name = graph.value(owner, HDF.name)
        if owner_name is not None:
            return f'{owner_name}@{name}'
    root = graph.value(node, HDF.rootGroup)
    if root is not None:
        return '/'
    return None


def parse_validation_report(data_graph, report_graph) -> tuple[Violation, ...]:
    """Map report entries to violations without changing either input graph."""
    violations = []
    for result_node in report_graph.subjects(rdflib.RDF.type, SH.ValidationResult):
        focus_node = report_graph.value(result_node, SH.focusNode)
        violations.append(Violation(
            focus_node=focus_node,
            property_path=report_graph.value(result_node, SH.resultPath),
            severity=report_graph.value(result_node, SH.resultSeverity),
            messages=tuple(str(message) for message in
                           report_graph.objects(result_node, SH.resultMessage)),
            hdf_path=_resolve_hdf_path(data_graph, focus_node),
        ))
    return tuple(violations)
