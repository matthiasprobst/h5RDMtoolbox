"""Scientific HDF5 access, semantic metadata, validation, and publication.

Public classes and feature modules are loaded when first requested. Importing
this package alone performs no filesystem or network operations.
"""
from __future__ import annotations

import json
import logging
import pathlib
from importlib import import_module
from typing import TYPE_CHECKING, Dict, Optional, Union

if TYPE_CHECKING:
    import rdflib
    from .ld._types import RDFMappingEntry
    from .wrapper.core import File, Group, Dataset, Lower, lower
    from .wrapper.h5attr import Attribute
    from .wrapper.accessor import register_accessor
    from ._cfg import set_config, get_config, get_ureg
    from .user import UserDir
    from .utils.download import DownloadFileManager
    from .database.lazy import lazy
    from .validation import validate
from ._version import __version__

__author__ = 'Matthias Probst'
__author_orcid__ = 'https://orcid.org/0000-0001-8729-0482'
__this_dir__ = pathlib.Path(__file__).parent
logger = logging.getLogger('h5rdmtoolbox')
logger.addHandler(logging.NullHandler())

_EXPORTS = {
    'File': ('.wrapper.core', 'File'),
    'Group': ('.wrapper.core', 'Group'),
    'Dataset': ('.wrapper.core', 'Dataset'),
    'Attribute': ('.wrapper.h5attr', 'Attribute'),
    'Lower': ('.wrapper.core', 'Lower'),
    'lower': ('.wrapper.core', 'lower'),
    'set_config': ('._cfg', 'set_config'),
    'get_config': ('._cfg', 'get_config'),
    'get_ureg': ('._cfg', 'get_ureg'),
    'UserDir': ('.user', 'UserDir'),
    'DownloadFileManager': ('.utils.download', 'DownloadFileManager'),
    'register_accessor': ('.wrapper.accessor', 'register_accessor'),
    'lazy': ('.database.lazy', 'lazy'),
    'validate': ('.validation', 'validate'),
}


def __getattr__(name):
    if name in _EXPORTS:
        module, symbol = _EXPORTS[name]
        value = getattr(import_module(module, __name__), symbol)
        globals()[name] = value
        return value
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def get_package_meta() -> Dict:
    """Return CodeMeta metadata from the installed package or editable checkout.

    Builds copy the canonical repository ``codemeta.json`` into package data;
    editable checkouts read that canonical source directly when needed.
    """
    from importlib_resources import files

    resource = files(__package__).joinpath('data/codemeta.json')
    try:
        text = resource.read_text(encoding='utf-8')
    except FileNotFoundError:
        source_root = __this_dir__.parent
        if source_root.name == 'src':
            source_root = source_root.parent
        if not (source_root / 'pyproject.toml').is_file():
            raise
        text = (source_root / 'codemeta.json').read_text(encoding='utf-8')
    return json.loads(text)


def dump(src: Union[str, File, pathlib.Path],
         *args, **kwargs) -> None:
    """Call h5.dump() on the provided HDF5 file

    Parameters
    ----------
    src : str, File, pathlib.Path
        the HDF5 file or filename to dump. An object which has a hdf_filename attribute can also be provided.
    kwargs
        kwargs passed to h5.dump(). See h5.dump() for more information.
    """
    from .wrapper.core import File
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dump(*args, **kwargs)

    if isinstance(src, (str, pathlib.Path)):
        pass
    else:
        if hasattr(src, 'hdf_filename'):
            src = src.hdf_filename

    with File(src) as h5:
        return h5.dump(**kwargs)


def dumps(src: Union[str, File, pathlib.Path]):
    """Call h5.dumps() on the provided HDF5 file

    Parameters
    ----------
    src : str, File, pathlib.Path
        the HDF5 file or filename to dump. An object which has a hdf_filename attribute can also be provided.
    """
    from .wrapper.core import File
    if isinstance(src, File):
        with File(src.hdf_filename) as h5:
            return h5.dumps()

    if isinstance(src, (str, pathlib.Path)):
        pass
    else:
        if hasattr(src, 'hdf_filename'):
            src = src.hdf_filename

    with File(src) as h5:
        return h5.dumps()


def get_ld(
        hdf_filename: Union[str, pathlib.Path],
        structural: bool = True,
        contextual: bool = True,
        skipND: int = 1,
        file_uri: Optional[str] = None,
        context: Optional[Dict] = None
) -> rdflib.Graph:
    """Return the HDF file content as a rdflib.Graph object."""
    from . import ld
    return ld.get_ld(
        hdf_filename,
        structural=structural,
        contextual=contextual,
        skipND=skipND,
        file_uri=file_uri,
        context=context,
    )


def _resolve_serialize_format(fmt: str, kwargs: Dict) -> str:
    return kwargs.pop("format", fmt)


def dump_jsonld(
        hdf_filename: Union[str, pathlib.Path],
        skipND: int = 1,
        indent: int = 2,
        structural: bool = True,
        contextual: bool = True,
        context: Optional[Dict] = None,
        file_uri: Optional[str] = None
):
    """Return the file content as a JSON-LD string."""
    graph = get_ld(hdf_filename,
                   structural=structural,
                   contextual=contextual,
                   file_uri=file_uri,
                   skipND=skipND)
    from .ld.utils import _serialize_graph
    return _serialize_graph(graph, fmt="json-ld", indent=indent, context=context)


def serialize(hdf_filename,
              fmt: str = "ttl",
              skipND: int = 1,
              structural: bool = True,
              contextual: bool = True,
              file_uri: Optional[Union[str, Dict[str, str]]] = None,
              rdf_mappings: Dict[str, RDFMappingEntry] = None,
              **kwargs):
    """Alternative to json-ld but allows multiple serialization options"""
    from .wrapper.core import File
    fmt = _resolve_serialize_format(fmt, kwargs)
    with File(hdf_filename) as h5:
        return h5.serialize(fmt=fmt,
                            skipND=skipND,
                            structural=structural,
                            contextual=contextual,
                            file_uri=file_uri,
                            rdf_mappings=rdf_mappings)


def sparql(
        hdf_filename: Union[str, pathlib.Path],
        query: str,
        structural: bool = True,
        contextual: bool = True,
        skipND: int = 1,
        file_uri: Optional[Union[str, Dict[str, str]]] = None,
        rdf_mappings: Dict[str, RDFMappingEntry] = None,
        as_dataframe: bool = False,
        **kwargs
) -> rdflib.query.Result:
    """Run a SPARQL query on the HDF5 file content. Returns a rdflib.query.Result object."""
    from .ld import sparql
    return sparql(
        source=hdf_filename,
        query=query,
        structural=structural,
        contextual=contextual,
        skipND=skipND,
        file_uri=file_uri,
        rdf_mappings=rdf_mappings,
        as_dataframe=as_dataframe,
        **kwargs
    )


def get_filesize(hdf_filename: Union[str, pathlib.Path]) -> int:
    """Get the size of the HDF5 file in bytes"""
    from . import utils
    return utils.get_filesize(hdf_filename)


def get_checksum(hdf_filename: Union[str, pathlib.Path]) -> str:
    """Get the checksum of the HDF5 file"""
    from . import utils
    return utils.get_checksum(hdf_filename)


def set_loglevel(level: Union[int, str]):
    """Set the logging level of the h5rdmtoolbox logger"""
    import logging
    _logger = logging.getLogger('h5rdmtoolbox')
    _logger.setLevel(level)
    for h in _logger.handlers:
        h.setLevel(level)

__all__ = tuple(_EXPORTS) + ('__version__', 'get_package_meta', 'serialize', 'get_ld', 'sparql')


def clean_temp_data(full=False):
    """Remove only temporary files owned by this process's directory manager."""
    import shutil
    from .user import UserDir
    directory = UserDir.user_dirs['tmp']
    if directory is not None and directory.exists():
        shutil.rmtree(directory)
