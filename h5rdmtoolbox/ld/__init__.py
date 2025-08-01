import pathlib
import warnings
from typing import Union, Optional

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
        semantic: Optional[bool] = None,
        skipND: Optional[int] = 1) -> rdflib.Graph:
    """Return the HDF file content as a rdflib.Graph object."""
    if skipND is not None:
        warnings.warn(
            "skipND is deprecated and will be removed in v1.8.0. Instead 'serialize_0d_datasets' is introduced, which enables the serialization of numerical or string 0D datasets.",
            DeprecationWarning)
    if semantic is not None:
        warnings.warn("semantic is deprecated and will be removed in v1.8.0. Use 'contextual' instead.",
                      DeprecationWarning)
        contextual = semantic

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
    return graph


def hdf2jsonld(
        filename: Union[str, pathlib.Path],
        metadata_filename: Optional[Union[str, pathlib.Path]] = None,
        fmt='json-ld',
        context: Optional[dict] = None,
        structural: bool = True,
        contextual: bool = True,
        indent: int = 2,
        file_uri: Optional[str] = None,
        **kwargs
):
    if metadata_filename is None:
        metadata_filename = pathlib.Path(filename).with_suffix('.jsonld')  # recommended suffix for JSON-LD is .jsonld!
    else:
        metadata_filename = pathlib.Path(metadata_filename)

    fmt = kwargs.pop("format", fmt)
    graph = get_ld(
        hdf_filename=filename,
        structural=structural,
        contextual=contextual,
        file_uri=file_uri,
        **kwargs
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
