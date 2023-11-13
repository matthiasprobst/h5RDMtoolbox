"""general validation functions of the toolbox usable by conventions. If users wish to user
their own validators, they need to define them separately. The respective python script then
must be provided during initialization of a Convention"""

import pint
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing import Union, Dict
from typing_extensions import Annotated

from h5rdmtoolbox import get_ureg, errors


def __validate_orcid(value, handler, info):
    from h5rdmtoolbox import orcid
    if not isinstance(value, str):
        raise TypeError(f'Expected a string but got {type(value)}')
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
        parent = info.context.get('parent', None)
        if parent is None:
            raise KeyError('No parent dataset found, which is needed to get the standard name table information!')

        attrs = info.context.get('attrs', None)
        if attrs is None:
            attrs = {}

        snt = info.context['parent'].rootparent.standard_name_table

        units = parent.attrs.get('units', None)
        if units is None:
            raise KeyError('No units defined for this variable!')

        # check if scale is provided:
        scale = attrs.get('scale',
                          parent.attrs.get('scale', None))
        if scale is not None:
            ureg = get_ureg()
            units = str((ureg.Quantity(scale) * ureg.Unit(units)).units)

        sn = snt[value]
        if sn.is_vector():
            raise errors.StandardAttributeError(f'Standard name {value} is a vector and cannot be used as '
                                                'attribute. Use a transformation e.g. with a component or magnitude '
                                                'instead.')
        if not sn.equal_unit(units):
            raise errors.StandardAttributeError(f'Standard name {value} has incompatible units {units}. '
                                                f'Expected units: {sn.units} but got {units}.')

        return sn
    raise ValueError(f'A standard name must be provided to check the validity of the name: {value}')


def __validate_url(value, handler, info):
    from h5rdmtoolbox.conventions.references import validate_url
    if not isinstance(value, (list, tuple)):
        references = [value, ]
    else:
        references = value

    for r in references:
        if not isinstance(r, str):
            raise TypeError(f'Expected a string but got {type(r)}')

    if all(validate_url(r) for r in references):
        if len(references) == 1:
            return references[0]
        return references
    raise ValueError(f'Invalid URL: {references}')


def __validate_quantity(value, handler, info):
    if isinstance(value, pint.Quantity):
        return value
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


def __validate_scale(value, handler, info):
    if not info.context:
        raise RuntimeError('Require context to validate offset!')
    parent = info.context.get('parent', None)
    if parent is None:
        raise RuntimeError('Require parent dataset to validate offset!')
    attrs = info.context.get('attrs', None)

    parent_group = info.context['parent'].parent

    if isinstance(value, str) and value in parent_group:
        return parent_group[value][()]

    raise KeyError(f'No dataset found with name {value}!')


def __validate_offset_or_scale(value, handler, info):
    if not info.context:
        raise RuntimeError('Require context to validate offset!')
    parent = info.context.get('parent', None)
    if parent is None:
        raise RuntimeError('Require parent dataset to validate offset!')

    parent_group = info.context['parent'].parent

    if isinstance(value, str):
        if value.startswith('/'):
            try:
                offset_or_scale_ds = parent.rootparent[value]
            except KeyError:
                raise KeyError(f'No dataset found with name {value}!')
        else:
            try:
                offset_or_scale_ds = parent_group[value]
            except KeyError:
                raise KeyError(f'No dataset found with name {value}!')
    else:
        raise TypeError(f'Offset dataset must be dataset name of dataset object, not {type(value)}')

    assert offset_or_scale_ds.ndim == 0

    offset_or_scale_ds_name = offset_or_scale_ds.name
    return offset_or_scale_ds_name


def __validate_date_format(value, handler, info):
    """value: str, e.g. '1991-01-19T13:45:05TZD'"""
    import dateutil.parser
    import warnings
    # will raise an error if not a valid datetime
    try:
        warnings.filterwarnings("error")
        dt = dateutil.parser.parse(value)
    except RuntimeWarning as e:
        raise ValueError(f'Invalid datetime: {value}. Original error: {e}')
    finally:
        warnings.filterwarnings("ignore")
    return dt


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
dateFormat = Annotated[str, WrapValidator(__validate_date_format)]
quantity = Annotated[str, WrapValidator(__validate_quantity)]
data_offset = Annotated[str, WrapValidator(__validate_offset_or_scale)]
data_scale = Annotated[str, WrapValidator(__validate_offset_or_scale)]
orcid = Annotated[str, WrapValidator(__validate_orcid)]
standard_name_table = Annotated[Union[str, Dict], WrapValidator(__validate_standard_name_table)]
standard_name = Annotated[str, WrapValidator(__validate_standard_name)]
url = Annotated[str, WrapValidator(__validate_url)]
