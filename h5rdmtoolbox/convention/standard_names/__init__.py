import json
import logging
import pathlib
from typing import Union

from h5rdmtoolbox._user import UserDir
from . import cache
from .h5interface import HDF5StandardNameInterface
from .name import StandardName
from .table import StandardNameTable
from ..consts import DefaultValue

logger = logging.getLogger('h5rdmtoolbox')


def parse_snt(snt: Union[str, dict, StandardNameTable]) -> StandardNameTable:
    """Returns a StandardNameTable object from a string, dict or StandardNameTable object"""
    if isinstance(snt, str):
        # could be web address or local file
        if snt[0] == '{':
            return StandardNameTable.from_dict(json.loads(snt))
        if 'zenodo.' in snt:
            return StandardNameTable.from_zenodo(snt)

        fname = pathlib.Path(snt)
        logger.debug(f'Reading standard name table from file {snt}')
        if fname.exists() and fname.suffix in ('.yaml', '.yml'):
            return StandardNameTable.from_yaml(fname)
        if snt in cache.snt:
            return cache.snt[snt]
        # maybe that's the name in the local dir:
        _fname = UserDir['standard_name_tables'] / fname.with_suffix('.yaml')
        if _fname.exists():
            return StandardNameTable.from_yaml(_fname)
        raise FileNotFoundError(f'File {fname} not found or not a yaml file')
    if isinstance(snt, StandardNameTable):
        return snt
    if isinstance(snt, dict):
        return StandardNameTable.from_dict(snt)
    if isinstance(snt, pathlib.Path):
        return parse_snt(str(snt))
    if isinstance(snt, DefaultValue):
        return parse_snt(snt.value)
    raise TypeError(f'Invalid type for standard_name_table: {type(snt)}')


__all__ = ['HDF5StandardNameInterface', 'parse_snt']
