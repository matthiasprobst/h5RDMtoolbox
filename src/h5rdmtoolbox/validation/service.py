"""Coordinate graph preparation, PySHACL execution and report parsing."""

import rdflib

from ._graphs import load_rdf_graph, prepare_data_graph
from .results import ValidationResult, parse_validation_report


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
    shapes_graph = load_rdf_graph(shapes, 'shapes')
    ontology_graph = None if ontology is None else load_rdf_graph(ontology, 'ontology')
    data_graph = prepare_data_graph(source, include_scalar_values)

    # Never let engine options turn this read-only service into an in-place
    # mutation of a caller-owned graph.
    if engine_options.pop('inplace', False):
        raise ValueError('In-place validation is not supported')
    from pyshacl import validate as validate_graph
    conforms, report_graph, report_text = validate_graph(
        data_graph, shacl_graph=shapes_graph, ont_graph=ontology_graph,
        inference=inference, inplace=False, **engine_options,
    )
    if not isinstance(report_graph, rdflib.Graph):
        raise RuntimeError(f'SHACL validation failed: {report_graph}')
    violations = parse_validation_report(data_graph, report_graph)
    return ValidationResult(bool(conforms), report_graph, str(report_text), violations)
