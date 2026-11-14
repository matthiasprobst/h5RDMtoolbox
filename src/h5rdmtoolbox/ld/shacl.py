"""HDF5 convenience adapter for the shared explicit validation service."""
from pathlib import Path

import rdflib

from ..validation import ValidationResult, validate


def validate_hdf(*, hdf_data=None, hdf_source=None, shacl_data=None,
                 shacl_source=None, hdf_file_uri="https://example.org/hdf5file#",
                 shacl_format="turtle", hdf_data_format="turtle", ont_graph=None,
                 ont_graph_format="turtle", merge_ont_graph_into_data=False,
                 include_scalar_values=False, **engine_options):
    """Validate HDF5 metadata using the shared SHACL service.

    Inline RDF is supported here for existing callers. New code can use
    ``validation.validate(source, shapes)`` with paths or RDFLib graphs.
    Validation never modifies caller-owned graphs or HDF5 files.
    """
    if (hdf_data is None) == (hdf_source is None):
        raise ValueError('Provide exactly one of hdf_data and hdf_source')
    if (shacl_data is None) == (shacl_source is None):
        raise ValueError('Provide exactly one of shacl_data and shacl_source')
    data = hdf_data if hdf_data is not None else hdf_source
    if isinstance(hdf_data, str):
        data = rdflib.Graph().parse(data=hdf_data, format=hdf_data_format)
    if hdf_source is not None:
        from . import get_ld
        data = get_ld(hdf_source, file_uri=hdf_file_uri,
                      include_scalar_values=include_scalar_values)
    shapes = shacl_data if shacl_data is not None else shacl_source
    if isinstance(shacl_data, str):
        shapes = rdflib.Graph().parse(data=shacl_data, format=shacl_format)
    elif shacl_source is not None:
        shapes = rdflib.Graph().parse(Path(shacl_source), format=shacl_format)
    ontology = ont_graph
    if isinstance(ont_graph, str):
        ontology = rdflib.Graph().parse(data=ont_graph, format=ont_graph_format)
    elif isinstance(ont_graph, Path):
        ontology = rdflib.Graph().parse(ont_graph, format=ont_graph_format)
    if merge_ont_graph_into_data and ontology is not None:
        data = data + ontology
        ontology = None
    # Preserve the old convenience entry point's inference default; the new
    # explicit service defaults to no inference.
    engine_options.setdefault('inference', 'rdfs')
    return validate(data, shapes, ontology=ontology,
                    include_scalar_values=include_scalar_values, **engine_options)
