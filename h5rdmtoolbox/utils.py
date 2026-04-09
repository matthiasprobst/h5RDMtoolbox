"""utilities of the h5rdmtoolbox.

.. deprecated::
    This module has been moved to the `h5rdmtoolbox.utils` package.
    All imports should now come from submodules:

    - ``h5rdmtoolbox.utils.file_io`` - File I/O utilities
    - ``h5rdmtoolbox.utils.download`` - Download and network utilities
    - ``h5rdmtoolbox.utils.hdf5`` - HDF5-specific utilities
    - ``h5rdmtoolbox.utils.string`` - String utilities
    - ``h5rdmtoolbox.utils.docstring`` - Docstring parsing utilities

    This file will be removed in version 3.0.0.

This module is kept for backward compatibility and re-exports all public
functions from the new submodule structure.
"""

import warnings

warnings.warn(
    "The 'h5rdmtoolbox.utils' module has been split into submodules. "
    "Please import from 'h5rdmtoolbox.utils' directly (which now uses submodules) "
    "or from specific submodules like 'h5rdmtoolbox.utils.file_io'. "
    "This file will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from h5rdmtoolbox.utils import (
    get_filesize,
    get_checksum,
    has_internet_connection,
    is_xml_file,
    sanitize_filename,
    generate_temporary_filename,
    generate_temporary_directory,
    download_file,
    download_context,
    DownloadFileManager,
    has_datasets,
    has_groups,
    create_h5tbx_version_grp,
    touch_tmp_hdf5_file,
    try_making_serializable,
    create_special_attribute,
    parse_object_for_attribute_setting,
    process_obj_filter_input,
    OBJ_FLT_DICT,
    remove_special_chars,
    DocStringParser,
    deprecated,
)

__all__ = [
    "get_filesize",
    "get_checksum",
    "has_internet_connection",
    "is_xml_file",
    "sanitize_filename",
    "generate_temporary_filename",
    "generate_temporary_directory",
    "download_file",
    "download_context",
    "DownloadFileManager",
    "has_datasets",
    "has_groups",
    "create_h5tbx_version_grp",
    "touch_tmp_hdf5_file",
    "try_making_serializable",
    "create_special_attribute",
    "parse_object_for_attribute_setting",
    "process_obj_filter_input",
    "OBJ_FLT_DICT",
    "remove_special_chars",
    "DocStringParser",
    "deprecated",
]
