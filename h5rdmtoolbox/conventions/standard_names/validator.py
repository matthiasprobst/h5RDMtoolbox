import pathlib
from typing import Union, Dict

from .table import StandardNameTable
from .. import errors, logger
from ..validators import StandardAttributeValidator, add_validator
from ... import get_ureg


def _parse_snt(snt: Union[str, dict, StandardNameTable]) -> StandardNameTable:
    """Returns a StandardNameTable object from a string, dict or StandardNameTable object"""
    if isinstance(snt, str):
        # could be web address or local file
        if snt.startswith('https://zenodo.org/record/') or snt.startswith('10.5281/zenodo.'):
            return StandardNameTable.from_zenodo(snt)
        fname = pathlib.Path(snt)
        logger.debug(f'Reading standard name table from file {snt}')
        if fname.exists() and fname.suffix in ('.yaml', '.yml'):
            return StandardNameTable.from_yaml(fname)
        raise FileNotFoundError(f'File {fname} not found or not a yaml file')
    if isinstance(snt, StandardNameTable):
        return snt
    if isinstance(snt, dict):
        return StandardNameTable.from_dict(snt)
    if isinstance(snt, pathlib.Path):
        return _parse_snt(str(snt))
    raise TypeError(f'Invalid type for standard_name_table: {type(snt)}')


class StandardNameTableValidator(StandardAttributeValidator):
    """Validates a standard name table"""

    keyword = '$standard_name_table'

    def __call__(self, standard_name_table, parent=None, attrs=None, **kwargs):
        # return parse_snt(standard_name_table).to_sdict()
        snt = _parse_snt(standard_name_table)
        if 'zenodo_doi' in snt.meta:
            return snt.meta['zenodo_doi']
        return snt.to_sdict()

    def get(self, value, parent):
        return _parse_snt(value)


class StandardNameValidator(StandardAttributeValidator):
    """Validator for attribute standard_name"""

    keyword = '$standard_name'

    def __call__(self, standard_name, parent, attrs: Dict = None):
        if attrs is None:
            attrs = {}
        snt = parent.rootparent.attrs.get('standard_name_table', None)

        if snt is None:
            raise KeyError('No standard name table defined for this file!')

        snt = _parse_snt(snt)  # TODO: cache this!

        units = parent.attrs.get('units', None)
        if units is None:
            raise KeyError('No units defined for this variable!')

        # check if scale is provided:
        scale = attrs.get('scale',
                          parent.attrs.get('scale', None))
        if scale is not None:
            ureg = get_ureg()
            units = str((ureg(scale) * ureg(units)).units)

        sn = snt[standard_name]
        if sn.is_vector():
            raise errors.StandardAttributeError(f'Standard name {standard_name} is a vector and cannot be used as '
                                                'attribute. Use a transformation e.g. with a component or magnitude '
                                                'instead.')
        if not sn.equal_unit(units):
            raise errors.StandardAttributeError(f'Standard name {standard_name} has incompatible units {units}. '
                                                f'Expected units: {sn.units} but got {units}.')

        return snt[standard_name].name


add_validator(StandardNameValidator)
add_validator(StandardNameTableValidator)
