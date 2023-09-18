
# ---- generated code: ----
from h5rdmtoolbox.conventions.toolbox_validators import *

    
from pydantic import BaseModel
# from pydantic.functional_validators import WrapValidator
# from typing_extensions import Annotated

import re

def regex_00_validator(value, parent=None, attrs=None):
    pattern = re.compile(r'^[a-zA-Z].{5,}$')
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


regex_00 = Annotated[int, WrapValidator(regex_00_validator)]
    
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
    value: regex_00


UnitsValidator(value="1")
