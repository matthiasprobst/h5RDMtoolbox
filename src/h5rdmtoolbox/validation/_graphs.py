"""Input preparation for explicit, read-only validation."""

from pathlib import Path

import h5py
import rdflib


def load_rdf_graph(value, label) -> rdflib.Graph:
    """Copy a caller-owned graph or parse a local RDF file."""
    if isinstance(value, rdflib.Graph):
        graph_copy = rdflib.Graph(bind_namespaces='none')
        for prefix, namespace in value.namespaces():
            graph_copy.bind(prefix, namespace)
        graph_copy += value
        return graph_copy
    if isinstance(value, (str, Path)):
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(path)
        return rdflib.Graph().parse(path, format=rdflib.util.guess_format(str(path)))
    raise TypeError(f'{label} must be an RDFLib Graph or a local file path')


def prepare_data_graph(source, include_scalar_values: bool) -> rdflib.Graph:
    """Accept an RDF graph or extract metadata from an HDF5 source."""
    if isinstance(source, rdflib.Graph):
        return source
    if isinstance(source, (str, Path, h5py.File)):
        from ..ld import get_ld
        return get_ld(source, include_scalar_values=include_scalar_values)
    raise TypeError('source must be an HDF5 path, open h5py.File, or RDFLib Graph')
