import inspect
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

import special_type_funcs

members = inspect.getmembers(special_type_funcs)

special_type_funcs_dict = {_func[0].strip('validate_'): Annotated[str, WrapValidator(_func[1])] for _func in
                           [m for m in members if inspect.isfunction(m[1]) if m[0].startswith('validate_')]}
special_type_funcs_dict['str'] = str
special_type_funcs_dict['int'] = int
special_type_funcs_dict['float'] = float


def get_special_type(name):
    _type = special_type_funcs_dict.get(name, None)
    if _type is None:
        raise ValueError(f'No type found for {name}')
    return _type

        
class PersonValidator(BaseModel):
    name: str
    age: int


class UnitsValidator(BaseModel):
    """The physical unit of the dataset. If dimensionless, the unit is ''."""
    value: get_special_type("units")


class SymbolValidator(BaseModel):
    """The mathematical symbol of the dataset."""
    value: str


UnitsValidator(value="8.4m")
