"""general validation functions of the toolbox usable by conventions. If users wish to user
their own validators, they need to define them separately. The respective python script then
must be provided during initialization of a Convention"""

import pint
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

from h5rdmtoolbox import get_ureg


def __validate_orcid(value, handler, info):
    from h5rdmtoolbox import orcid
    oid = orcid.ORCID(value)
    if not oid.exists():
        raise ValueError(f'Not an ORCID ID: {oid}')
    return oid


def __validate_standard_name_table(value, handler, info) -> "StandardNameTable":
    from h5rdmtoolbox.conventions import standard_names
    return standard_names.parse_snt(value)


def __validate_standard_name(value, handler, info) -> "StandardNameTable":
    from h5rdmtoolbox.conventions import standard_names
    if not isinstance(value, (str, standard_names.StandardName)):
        raise TypeError(f'Expected a string or StandardName object, got {type(value)}')
    if info.context:
        snt = info.context['parent'].rootparent.standard_name_table
        return snt[value]
    raise ValueError(f'A standard name must be provided to check the validity of the name: {value}')


def __validate_quantity(value, handler, info):
    try:
        return get_ureg().Quantity(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Quantity cannot be understood using ureg package: {quantity}. Original error: {e}')


def __validate_units(value, handler, info):
    """validate units using pint package"""
    try:
        return get_ureg().Unit(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')


def __validate_offset(value, handler, info):
    if info.context:
        parent = info.context.get('parent', None)
        attrs = info.context.get('attrs', None)

    qoffset = get_ureg().Quantity(value)

    if attrs:
        scale = attrs.get('scale', parent.attrs.get('scale', None))
        ds_units = attrs.get('units', parent.attrs.get('units', None))
    else:
        scale = parent.attrs.get('scale', None)
        ds_units = parent.attrs.get('units', None)

    if scale is not None:
        scale = get_ureg().Quantity(scale)

    if ds_units is None:
        if scale is None:
            # dataset has no units and no scale given, thus offset must be dimensionless
            if qoffset.dimensionality != pint.dimensionless.dimensionality:
                raise ValueError(f'Offset must be dimensionless if no units are given. '
                                 f'Got: {qoffset.dimensionality}')
        else:
            # scale is given but dataset is dimensionless, scale and offset must have same units
            if qoffset.dimensionality != scale.dimensionality:
                raise ValueError(f'Offset and scale must have same units if dataset is dimensionless. '
                                 f'Got: {qoffset.dimensionality} and {scale.dimensionality}')
    else:
        ds_units = get_ureg().Unit(ds_units)
        # dataset has units, offset must either have units of dataset or product of scale and dataset
        from .utils import equal_base_units
        if scale is None:
            resulting_units = ds_units
        else:
            resulting_units = get_ureg().Unit(f'{ds_units} {scale.units}')
        if not equal_base_units(qoffset.units, ds_units) and not equal_base_units(qoffset.units, resulting_units):
            raise ValueError(f'Offset must have same units as dataset or product of scale and dataset. '
                             f'Got: {qoffset.units} and {ds_units}')
    return qoffset


def _get_validate_type(_type):
    def __validate_type(value, handler, info):
        if not isinstance(value, _type):
            raise TypeError(f'Value must be a string but got {type(value)}')
        return value

    return __validate_type


class StringValidator(BaseModel):
    value: Annotated[str, WrapValidator(_get_validate_type(str))]


class FloatValidator(BaseModel):
    value: Annotated[str, WrapValidator(_get_validate_type(float))]


class IntValidator(BaseModel):
    value: Annotated[str, WrapValidator(_get_validate_type(int))]


units = Annotated[str, WrapValidator(__validate_units)]
quantity = Annotated[str, WrapValidator(__validate_quantity)]
offset = Annotated[str, WrapValidator(__validate_offset)]
orcid = Annotated[str, WrapValidator(__validate_orcid)]
standard_name_table = Annotated[str, WrapValidator(__validate_standard_name_table)]
standard_name = Annotated[str, WrapValidator(__validate_standard_name)]
