"""Explicit SHACL validation of HDF5 metadata and RDF graphs."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import h5py
import rdflib
from rdflib.namespace import SH

HDF = rdflib.Namespace('http://purl.allotrope.org/ontologies/hdf5/1.8#')


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
    def messages(self):
        return [message for item in self.violations for message in item.messages]

    @property
    def nodes(self):
        return [item.focus_node for item in self.violations]


def _graph(value, label):
    if isinstance(value, rdflib.Graph):
        copy = rdflib.Graph(bind_namespaces='none')
        for prefix, namespace in value.namespaces():
            copy.bind(prefix, namespace)
        copy += value
        return copy
    if isinstance(value, (str, Path)):
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(path)
        return rdflib.Graph().parse(path, format=rdflib.util.guess_format(str(path)))
    raise TypeError(f'{label} must be an RDFLib Graph or a local file path')


def _hdf_path(graph, node):
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


def validate(source, shapes, *, include_scalar_values=False, ontology=None,
             inference='none', **engine_options):
    """Validate structure and metadata without reading array payloads.

    Parameters
    ----------
    source : path, h5py.File, or rdflib.Graph
        HDF5 source or an already prepared data graph. Open files remain open.
    shapes : path or rdflib.Graph
        Standard SHACL shapes. Parse inline RDF into a Graph explicitly.
    include_scalar_values : bool, default=False
        Include raw scalar dataset values in both graph views. Array data is
        never extracted by this API. Attribute values remain part of metadata.
    ontology : path or rdflib.Graph, optional
        Ontology supplied to the validation engine without modifying inputs.
    inference : str, default='none'
        PySHACL inference mode, explicitly enabled by callers when required.
    **engine_options
        Additional PySHACL settings, for example ``advanced=True``.

    Returns
    -------
    ValidationResult
        A nonconforming graph is a result. Invalid input and engine failures
        raise exceptions rather than being reported as valid or nonconforming.
    """
    if not isinstance(include_scalar_values, bool):
        raise TypeError('include_scalar_values must be a bool')
    shapes_graph = _graph(shapes, 'shapes')
    ontology_graph = None if ontology is None else _graph(ontology, 'ontology')
    if isinstance(source, rdflib.Graph):
        data = source
    elif isinstance(source, (str, Path, h5py.File)):
        from ..ld import get_ld
        data = get_ld(source, include_scalar_values=include_scalar_values)
    else:
        raise TypeError('source must be an HDF5 path, open h5py.File, or RDFLib Graph')

    # Never let engine options turn this read-only service into an in-place
    # mutation of a caller-owned graph.
    if engine_options.pop('inplace', False):
        raise ValueError('In-place validation is not supported')
    from pyshacl import validate as validate_graph
    conforms, report, report_text = validate_graph(
        data, shacl_graph=shapes_graph, ont_graph=ontology_graph,
        inference=inference, inplace=False, **engine_options,
    )
    if not isinstance(report, rdflib.Graph):
        raise RuntimeError(f'SHACL validation failed: {report}')
    violations = []
    for result in report.subjects(rdflib.RDF.type, SH.ValidationResult):
        focus = report.value(result, SH.focusNode)
        violations.append(Violation(
            focus_node=focus,
            property_path=report.value(result, SH.resultPath),
            severity=report.value(result, SH.resultSeverity),
            messages=tuple(str(message) for message in report.objects(result, SH.resultMessage)),
            hdf_path=_hdf_path(data, focus),
        ))
    return ValidationResult(bool(conforms), report, str(report_text), tuple(violations))


__all__ = ['validate', 'ValidationResult', 'Violation']
