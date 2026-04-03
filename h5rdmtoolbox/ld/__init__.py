import pathlib
from typing import Dict, Optional, Union

import h5py
import rdflib

from ._types import RDFMappingEntry
from .hdf.file import get_ld as get_hdf_ld
from .sparql import sparql
from .user.file import get_ld as get_contextual_ld
from .utils import optimize_context

BINARY_AS_STRING = True

__all__ = ["get_ld", "hdf2jsonld", "hdf2ttl", "sparql"]


def _validate_file_uri(file_uri: Optional[str]) -> None:
    if file_uri and not (str(file_uri).endswith("#") or str(file_uri).endswith("/")):
        raise ValueError("file_uri must end with '#' or '/'")


def _build_ld_graph(
        h5_file: h5py.File,
        *,
        structural: bool,
        contextual: bool,
        file_uri: Optional[str],
        skipND: Optional[int],
        rdf_mappings: Optional[Dict[str, RDFMappingEntry]],
) -> Optional[rdflib.Graph]:
    """Build the requested graph variant from one open HDF5 file handle."""
    if structural and contextual:
        structural_graph = get_hdf_ld(h5_file, file_uri=file_uri, skipND=skipND)
        contextual_graph = get_contextual_ld(
            h5_file,
            file_uri=file_uri,
            rdf_mappings=rdf_mappings,
        )
        return structural_graph + contextual_graph
    if structural:
        return get_hdf_ld(h5_file, file_uri=file_uri, skipND=skipND)
    if contextual:
        # Keep historical behavior: contextual-only requests ignore rdf_mappings.
        return get_contextual_ld(h5_file, file_uri=file_uri)
    return None


def _bind_context_to_graph(graph: rdflib.Graph, context: Optional[Dict]) -> None:
    """Bind user context entries exactly like before."""
    if not context:
        return
    for _prefix, uri in context.items():
        if not isinstance(uri, rdflib.URIRef):
            graph.bind("ex", rdflib.URIRef(uri))


def _resolve_output_suffix(fmt: str) -> str:
    if fmt in ("json", "json-ld", "jsonld"):
        return ".jsonld"
    if fmt in ("turtle", "ttl"):
        return ".ttl"
    raise ValueError(f"Format '{fmt}' currently not supported. Use 'json-ld' or 'ttl'.")


def _resolve_metadata_filename(
        filename: Union[str, pathlib.Path],
        metadata_filename: Optional[Union[str, pathlib.Path]],
        suffix: str,
) -> pathlib.Path:
    if metadata_filename is None:
        # Recommended suffix for JSON-LD is .jsonld.
        return pathlib.Path(filename).with_suffix(suffix)
    return pathlib.Path(metadata_filename)


def _serialize_graph(
        graph: rdflib.Graph,
        fmt: str,
        indent: int,
        context: Optional[dict],
) -> str:
    optimized_context = optimize_context(graph, context or {})
    return graph.serialize(
        format=fmt,
        indent=indent,
        auto_compact=True,
        context=optimized_context,
    )


def get_ld(
        hdf_filename: Union[str, pathlib.Path],
        structural: bool = True,
        contextual: bool = True,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
        context: Optional[Dict] = None,
        rdf_mappings: Dict[str, RDFMappingEntry] = None,
) -> rdflib.Graph:
    """Return the HDF file content as an RDF graph.

    Extracts metadata and structure from an HDF5 file and returns it as an rdflib.Graph
    object. The graph can contain structural RDF (representing the HDF5 hierarchy)
    and/or contextual RDF (semantic mappings from attributes to ontologies).

    Parameters
    ----------
    hdf_filename : Union[str, pathlib.Path]
        Path to the HDF5 file.
    structural : bool, default=True
        Include structural RDF representing HDF5 groups, datasets, and attributes.
    contextual : bool, default=True
        Include contextual RDF from attribute-to-ontology mappings.
    file_uri : Optional[str], default=None
        Base URI for file resources. Must end with '#' or '/'.
    skipND : Optional[int], default=1
        Number of dimensions to skip for nested dataset data.
    context : Optional[Dict], default=None
        Additional namespace prefixes to bind in the graph.
    rdf_mappings : Optional[Dict[str, RDFMappingEntry]], default=None
        Custom RDF mappings for attributes.

    Returns
    -------
    rdflib.Graph
        An RDF graph containing the HDF5 metadata.

    Raises
    ------
    ValueError
        If both structural and contextual are False, or if file_uri format is invalid.
    """
    _validate_file_uri(file_uri)

    with h5py.File(hdf_filename) as h5:
        graph = _build_ld_graph(
            h5,
            structural=structural,
            contextual=contextual,
            file_uri=file_uri,
            skipND=skipND,
            rdf_mappings=rdf_mappings,
        )
    if graph is None:
        raise ValueError("structural and semantic cannot be both False.")
    _bind_context_to_graph(graph, context)
    return graph


def hdf2jsonld(
        filename: Union[str, pathlib.Path],
        metadata_filename: Optional[Union[str, pathlib.Path]] = None,
        context: Optional[dict] = None,
        structural: bool = True,
        contextual: bool = True,
        indent: int = 2,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
):
    """Export HDF5 file metadata to JSON-LD format.

    Converts HDF5 file metadata to a JSON-LD file, including both structural
    RDF (groups, datasets, attributes) and contextual RDF (semantic mappings).

    Parameters
    ----------
    filename : Union[str, pathlib.Path]
        Path to the HDF5 file.
    metadata_filename : Optional[Union[str, pathlib.Path]], default=None
        Output path for the JSON-LD file. If None, uses the HDF5 filename
        with .jsonld extension.
    context : Optional[dict], default=None
        Additional JSON-LD context definitions.
    structural : bool, default=True
        Include structural RDF from HDF5 hierarchy.
    contextual : bool, default=True
        Include contextual RDF from attribute mappings.
    indent : int, default=2
        JSON indentation level.
    file_uri : Optional[str], default=None
        Base URI for the file resources.
    skipND : Optional[int], default=1
        Number of dimensions to skip for nested data.

    Returns
    -------
    pathlib.Path
        Path to the generated JSON-LD file.
    """
    return _hdf2ld(
        filename=filename,
        fmt="json-ld",
        metadata_filename=metadata_filename,
        context=context,
        structural=structural,
        contextual=contextual,
        indent=indent,
        file_uri=file_uri,
        skipND=skipND,
    )


def hdf2ttl(
        filename: Union[str, pathlib.Path],
        metadata_filename: Optional[Union[str, pathlib.Path]] = None,
        context: Optional[dict] = None,
        structural: bool = True,
        contextual: bool = True,
        indent: int = 2,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
):
    """Export HDF5 file metadata to Turtle (TTL) format.

    Converts HDF5 file metadata to a Turtle RDF file, including both structural
    RDF (groups, datasets, attributes) and contextual RDF (semantic mappings).

    Parameters
    ----------
    filename : Union[str, pathlib.Path]
        Path to the HDF5 file.
    metadata_filename : Optional[Union[str, pathlib.Path]], default=None
        Output path for the Turtle file. If None, uses the HDF5 filename
        with .ttl extension.
    context : Optional[dict], default=None
        Additional namespace prefix definitions.
    structural : bool, default=True
        Include structural RDF from HDF5 hierarchy.
    contextual : bool, default=True
        Include contextual RDF from attribute mappings.
    indent : int, default=2
        Turtle indentation level.
    file_uri : Optional[str], default=None
        Base URI for the file resources.
    skipND : Optional[int], default=1
        Number of dimensions to skip for nested data.

    Returns
    -------
    pathlib.Path
        Path to the generated Turtle file.
    """
    return _hdf2ld(
        filename=filename,
        fmt="ttl",
        metadata_filename=metadata_filename,
        context=context,
        structural=structural,
        contextual=contextual,
        indent=indent,
        file_uri=file_uri,
        skipND=skipND,
    )


def _hdf2ld(
        filename: Union[str, pathlib.Path],
        fmt: str,
        metadata_filename: Optional[Union[str, pathlib.Path]] = None,
        context: Optional[dict] = None,
        structural: bool = True,
        contextual: bool = True,
        indent: int = 2,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
):
    suffix = _resolve_output_suffix(fmt)
    metadata_filename = _resolve_metadata_filename(filename, metadata_filename, suffix)

    graph = get_ld(
        hdf_filename=filename,
        structural=structural,
        contextual=contextual,
        file_uri=file_uri,
        skipND=skipND,
    )

    with open(metadata_filename, "w", encoding="utf-8") as f:
        f.write(_serialize_graph(graph, fmt=fmt, indent=indent, context=context))

    return metadata_filename
