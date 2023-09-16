import pint

from h5rdmtoolbox import get_ureg


def validate_units(value, handler, info):
    """validate units using pint package"""
    try:
        get_ureg().Unit(value)
    except (pint.UndefinedUnitError, TypeError) as e:
        raise ValueError(f'Units cannot be understood using ureg package: {value}. Original error: {e}')
    return str(value)

    
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated


# ---- generated code: ----
units = Annotated[str, WrapValidator(validate_units)]


class PersonValidator(BaseModel):
    name: str
    age: int = 3


class UnitsValidator(BaseModel):
    """The physical unit of the dataset. If dimensionless, the unit is ''."""
    value: units


class SymbolValidator(BaseModel):
    """The mathematical symbol of the dataset."""
    value: str


class Long_nameValidator(BaseModel):
    """A very long name."""
    value: regex(^[a-zA-Z].*(?<!\s)$)


UnitsValidator(value="1")
