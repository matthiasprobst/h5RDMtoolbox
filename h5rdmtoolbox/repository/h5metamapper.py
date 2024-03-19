import h5py
import json
import logging
import numpy as np
import pathlib
from typing import Union

logger = logging.getLogger('h5rdmtoolbox')


def _parse_dtype(v):
    if isinstance(v, np.int32):
        return int(v)
    if isinstance(v, np.int64):
        return int(v)
    if isinstance(v, np.float32):
        return float(v)
    if isinstance(v, np.float64):
        return float(v)
    if isinstance(v, np.ndarray):
        return [_parse_dtype(value) for value in v.tolist()]
    if isinstance(v, str):
        return v
    if v is None:
        return None
    return str(v)


def _extract_metadata(group):
    metadata = {'attrs': {k: _parse_dtype(v) for k, v in group.attrs.items() if k not in ('REFERENCE_LIST', 'CLASS')}}

    # Iterate over all items (datasets and subgroups) in the group
    for name, item in group.items():
        if isinstance(item, h5py.Group):
            # Recursively extract metadata for subgroups
            metadata[name] = _extract_metadata(item)
        elif isinstance(item, h5py.Dataset):
            # Extract metadata for datasets
            properties = {'shape': item.shape,
                          'dtype': str(item.dtype)}
            metadata[name] = {
                'props': properties,
                'attrs': {k: _parse_dtype(v) for k, v in item.attrs.items() if k not in ('REFERENCE_LIST', 'CLASS')}
            }

    return metadata


def hdf2json(file_or_filename: Union[str, pathlib.Path, h5py.Group],
             json_filename: Union[None, str, pathlib.Path] = None) -> pathlib.Path:
    """Convert an HDF5 file to a JSON file."""
    if not isinstance(file_or_filename, h5py.Group):
        hdf_filename = file_or_filename
        with h5py.File(file_or_filename, 'r') as f:
            h5dict = _extract_metadata(f)
    else:
        hdf_filename = file_or_filename.filename
        h5dict = _extract_metadata(file_or_filename)

    if json_filename is None:
        json_filename = pathlib.Path(hdf_filename).with_suffix('.json')
    else:
        json_filename = pathlib.Path(json_filename)
    with open(json_filename, 'w') as json_file:
        json.dump(h5dict, json_file, indent=2)

    return json_filename
