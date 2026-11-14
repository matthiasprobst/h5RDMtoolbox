"""Small shared wrapper helpers independent of concrete object classes."""
from __future__ import annotations

import logging
import pathlib
import warnings
from datetime import datetime
from typing import Dict, Union, Tuple, Optional

import numpy as np


logger = logging.getLogger("h5rdmtoolbox")

MODIFIABLE_PROPERTIES_OF_A_DATASET = (
    "name",
    "chunks",
    "compression",
    "compression_opts",
    "dtype",
    "maxshape",
)

H5KWARGS = (
    "driver",
    "libver",
    "userblock_size",
    "swmr",
    "rdcc_nslots",
    "rdcc_nbytes",
    "rdcc_w0",
    "track_order",
    "fs_strategy",
    "fs_persist",
    "fs_threshold",
    "fs_page_size",
    "page_buf_size",
    "min_meta_keep",
    "min_raw_keep",
    "locking",
    "alignment_threshold",
    "alignment_interval",
    "meta_block_size",
)

ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

def assert_filename_existence(filename: pathlib.Path) -> pathlib.Path:
    """Raises an error if the filename does not exist. Otherwise, the filename is returned.

    Parameters
    ----------
    filename : pathlib.Path
        Filename to check.

    Returns
    -------
    pathlib.Path
        The filename if it exists.

    Raises
    ------
    FileNotFoundError
        If the filename does not exist.
    """
    if not filename.exists():
        raise FileNotFoundError(
            "Filename does not exist. It might be moved or deleted!"
        )
    return filename

def convert_strings_to_datetimes(array, time_format="%Y-%m-%dT%H:%M:%S.%f"):
    assert np.issubdtype(array.dtype, np.str_), "Unexpected array type"
    time_format = _normalize_time_format(time_format)
    return np.array(
        [datetime.strptime(date_str, time_format) for date_str in array.flat]
    ).reshape(array.shape)

class Lower(str):
    """Lower"""

    def __new__(cls, string):
        instance = super().__new__(cls, string.lower())
        return instance

def lower(string: str) -> str:
    """return object Lower(string). Used when a dataset
    is called, but the upper/lower case should be irrelevant."""
    return Lower(string)


def _delattr(obj, item):
    del obj[item]

def _normalize_time_format(time_format: str) -> str:
    if isinstance(time_format, str) and time_format.lower() == "iso":
        return ISO_TIME_FORMAT
    return time_format

def _validate_jsonld_file_uri(file_uri: Optional[str]) -> None:
    if file_uri is not None and not file_uri.endswith("#"):
        raise ValueError(
            "The base URI for semantic metadata describing HDF5 internals must end with '#' to indicate that "
            "fragment identifiers (e.g., '#entry/data') refer to conceptual parts of the file. Without the '#', "
            "it would incorrectly suggest that internal components are resolvable sub-resources on the web."
        )

def _warn_on_missing_file_uri(file_uri: Optional[Union[str, Dict]]) -> None:
    if file_uri is None:
        warnings.warn(
            "Not providing a file-uri is not good practice because it will generate blank nodes. Consider providing an URI such as the DOI URL for example.",
            category=UserWarning,
        )

def _normalize_file_uri_and_prefix(
    file_uri: Optional[Union[str, Dict]],
) -> Tuple[Optional[Union[str, Dict]], Optional[str]]:
    if not isinstance(file_uri, Dict):
        return file_uri, None

    if len(file_uri) != 1:
        raise ValueError(
            "If file_uri is a dict, it must contain exactly one key-value pair."
        )

    prefix, normalized_file_uri = next(iter(file_uri.items()))
    return normalized_file_uri, prefix

class DatasetValues:
    """helper class to work around xarray"""

    def __init__(self, h5dataset):
        self.h5dataset = h5dataset

    def __getitem__(self, args, new_dtype=None):
        return self.h5dataset.__getitem__(args, new_dtype=new_dtype, nparray=True)

    def __setitem__(self, args, val):
        return self.h5dataset.__setitem__(args, val)

def only_0d_and_1d(obj):
    """Decorator to check if the dataset is 1D"""

    def wrapper(*args):
        if args[0].ndim > 1:
            raise ValueError("Only applicable to 0D and 1D datasets!")

    return obj
