"""general validation functions of the toolbox usable by conventions. If users wish to user
their own validators, they need to define them separately. The respective python script then
must be provided during initialization of a Convention"""

import pint
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

from h5rdmtoolbox import get_ureg


def __validate_units(value, handler, info):
    """validate units using pint package"""
    try:
        return get_ureg().Unit(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')


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
