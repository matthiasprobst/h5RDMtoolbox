"""Utilities for h5rdmtoolbox.

This module has been split into submodules:
- h5rdmtoolbox.utils.file_io: File I/O utilities
- h5rdmtoolbox.utils.download: Download and network utilities
- h5rdmtoolbox.utils.hdf5: HDF5-specific utilities
- h5rdmtoolbox.utils.string: String utilities
- h5rdmtoolbox.utils.docstring: Docstring parsing utilities

Import from the new submodules for new code. The re-exports in this
module will be removed in version 3.0.0.
"""

from .file_io import (
    get_filesize,
    get_checksum,
    has_internet_connection,
    is_xml_file,
    sanitize_filename,
    generate_temporary_filename,
    generate_temporary_directory,
    _request_with_backoff,
    _download_file,
)

from .download import (
    download_file,
    download_context,
    DownloadFileManager,
    USER_AGENT_HEADER,
)

from .hdf5 import (
    has_datasets,
    has_groups,
    create_h5tbx_version_grp,
    touch_tmp_hdf5_file,
    try_making_serializable,
    create_special_attribute,
    parse_object_for_attribute_setting,
    process_obj_filter_input,
    OBJ_FLT_DICT,
    _has_object_type,
)

from .string import remove_special_chars

from .docstring import DocStringParser, deprecated

__all__ = [
    # file_io
    "get_filesize",
    "get_checksum",
    "has_internet_connection",
    "is_xml_file",
    "sanitize_filename",
    "generate_temporary_filename",
    "generate_temporary_directory",
    "_request_with_backoff",
    "_download_file",
    # download
    "download_file",
    "download_context",
    "DownloadFileManager",
    "USER_AGENT_HEADER",
    # hdf5
    "has_datasets",
    "has_groups",
    "_has_object_type",
    "create_h5tbx_version_grp",
    "touch_tmp_hdf5_file",
    "try_making_serializable",
    "create_special_attribute",
    "parse_object_for_attribute_setting",
    "process_obj_filter_input",
    "OBJ_FLT_DICT",
    # string
    "remove_special_chars",
    # docstring
    "DocStringParser",
    "deprecated",
]
