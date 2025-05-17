import pathlib
import types
from typing import Union, Dict

import pint
import rdflib
from ontolutils.utils.qudt_units import qudt_lookup
from pydantic import HttpUrl, FileUrl
from pydantic.functional_validators import WrapValidator
from ssnolib import StandardNameTable, dcat, parse_table
from typing_extensions import Annotated

from h5rdmtoolbox import get_ureg
from h5rdmtoolbox.errors import StandardAttributeError

_snt = None

inverse_qudt_lookup = {v: k for k, v in qudt_lookup.items()}


def __validate_standard_name_table(value, handler, info) -> StandardNameTable:
    global _snt

    def _parse_web_or_file_url(value):
        if isinstance(value, str):
            if value.startswith("http"):
                return HttpUrl(value)
            if pathlib.Path(value).exists():
                return FileUrl(value)
            try:
                return FileUrl(value)
            except ValueError:
                return HttpUrl(value)
        return value

    value = _parse_web_or_file_url(value)

    def __snt_h5attr_repr__(self):
        return value

    _snt_filename = dcat.Distribution(downloadURL=value).download()
    _snt = parse_table(source=_snt_filename)
    _snt.__h5attr_repr__ = types.MethodType(__snt_h5attr_repr__, _snt)
    return _snt


def equal_base_units(u1: Union[str, pint.Unit, pint.Quantity],
                     u2: Union[str, pint.Unit, pint.Quantity]) -> bool:
    """Returns True if base units are equal, False otherwise"""

    def _convert(u):
        if isinstance(u, str):
            if u.startswith("http"):
                return 1 * get_ureg()(inverse_qudt_lookup.get(rdflib.URIRef(u), ''))
            return 1 * get_ureg()(u.strip())
        if isinstance(u, pint.Unit):
            return 1 * u
        if isinstance(u, pint.Quantity):
            return u
        raise TypeError(f"u must be a str, pint.Unit or pint.Quantity, not {type(u)}")

    return _convert(u1).to_base_units().units == _convert(u2).to_base_units().units


def __validate_standard_name(value, handler, info) -> str:
    """Verify that version is a valid as defined in https://semver.org/"""

    def __sn_h5attr_repr__(self):
        if isinstance(value, str):
            return str(value)

    if info.context:
        parent = info.context.get('parent', None)
    else:
        raise StandardAttributeError(
            'No parent dataset found, which is needed to get the standard name table information!')

    if _snt is None:
        raise ValueError('Standard name table is not set!')
    sn = _snt.get_standard_name(value)
    if sn is None:
        raise ValueError(f'Standard name not part of the table: "{value}"')
    # check unit:
    units = parent.attrs.get('units', None)
    if units is None:
        raise StandardAttributeError('No units defined for this variable!')

    if not equal_base_units(sn.unit, units):
        raise StandardAttributeError(f'Standard name {value} has incompatible units {units}. '
                                     f'Expected units: {sn.unit} but got {units}.')
    sn.__h5attr_repr__ = types.MethodType(__sn_h5attr_repr__, _snt)
    return sn


standardNameTableType = Annotated[Union[str, Dict], WrapValidator(__validate_standard_name_table)]

standardNameType = Annotated[str, WrapValidator(__validate_standard_name)]
