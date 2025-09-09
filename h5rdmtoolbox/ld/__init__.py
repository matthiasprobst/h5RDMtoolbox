import pathlib
from typing import Union, Optional, Dict

import h5py
import rdflib

from .hdf.file import get_ld as get_hdf_ld
from .user.file import get_ld as get_contextual_ld
from .utils import optimize_context


def get_ld(
        hdf_filename: Union[str, pathlib.Path],
        structural: bool = True,
        contextual: bool = True,
        file_uri: Optional[str] = None,
        skipND: Optional[int] = 1,
        context: Optional[Dict] = None) -> rdflib.Graph:
    """Return the HDF file content as a rdflib.Graph object."""

    graph = None
    with h5py.File(hdf_filename) as h5:
        if contextual and structural:
            graph1 = get_hdf_ld(h5, file_uri=file_uri, skipND=skipND)
            graph2 = get_contextual_ld(h5, file_uri=file_uri)
            graph = graph1 + graph2
        else:
            if structural:
                graph = get_hdf_ld(hdf_filename, file_uri=file_uri, skipND=skipND)

            if contextual:
                graph = get_contextual_ld(hdf_filename, file_uri=file_uri)
    if graph is None:
        raise ValueError("structural and semantic cannot be both False.")
    context = context or {}
    for prefix, uri in context.items():
        if not isinstance(uri, rdflib.URIRef):
            graph.bind("ex", rdflib.URIRef(uri))
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
    return _hdf2ld(
        filename=filename,
        fmt='json-ld',
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
    return _hdf2ld(
        filename=filename,
        fmt='ttl',
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
    if fmt in ('json', 'json-ld', 'jsonld'):
        suffix = '.jsonld'
    elif fmt in ('turtle', 'ttl'):
        suffix = '.ttl'
    else:
        raise ValueError(f"Format '{fmt}' currently not supported. Use 'json-ld' or 'ttl'.")
    if metadata_filename is None:
        metadata_filename = pathlib.Path(filename).with_suffix(suffix)  # recommended suffix for JSON-LD is .jsonld!
    else:
        metadata_filename = pathlib.Path(metadata_filename)

    graph = get_ld(
        hdf_filename=filename,
        structural=structural,
        contextual=contextual,
        file_uri=file_uri,
        skipND=skipND
    )
    context = context or {}
    context = optimize_context(graph, context)

    with open(metadata_filename, 'w', encoding='utf-8') as f:
        f.write(
            graph.serialize(format=fmt,
                            indent=indent,
                            auto_compact=True,
                            context=context)
        )

    return metadata_filename
