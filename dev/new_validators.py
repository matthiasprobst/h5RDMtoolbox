def write_pattern_validator(name, pattern):
    with open('_my_valiator.py', 'w') as f:
        validator_name = name.strip('$')
        lines = f"""
from pydantic import (
    BaseModel,
)
from validator_types import validator_types, WrapValidator, Annotated
import re

def _{name}(value, parent=None, attrs=None):
    pattern = re.compile(r"{pattern}")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value

regex = Annotated[int, WrapValidator(_{name})]

class {validator_name.capitalize()}Validator(BaseModel):"""
        f.writelines(lines)
        line = f'\n\t{name}: regex'
        f.write(line)


def write_validator(name='$contact', types={'name': 'str', 'orcid': {'regex': r'^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$'}}):
    with open('_my_valiator.py', 'w') as f:
        validator_name = name.strip('$')
        lines = """
from pydantic import (
    BaseModel,
)
from validator_types import validator_types, WrapValidator, Annotated
import re

def regex_0(value, parent=None, attrs=None):
    pattern = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value
    
regex = Annotated[int, WrapValidator(regex_0)]"""
        lines += f"""
class {validator_name.capitalize()}Validator(BaseModel):"""
        f.writelines(lines)
        for key, value in types.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if k == 'regex':
                        line = f'\n\t{key}: regex'
                    break
            else:
                line = f'\n\t{key}: validator_types.get("{value}")'
            f.write(line)


# write_pattern_validator('regex_validator', r'^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$')

# orcid = Annotated[int, WrapValidator(validate_orcid_format)]
#
#
# def get_orcid_validator():
#     return Annotated[int, WrapValidator(validate_orcid_format)]


# testing:
from _my_valiator import ContactValidator

# class PersonValidator(BaseModel):
#     name: str
#     id: validator_types.get('orcid')


user_input = {'name': 'hallo', 'orcid': '0000-0001-2345-678X'}
m = ContactValidator(**user_input)

# def get_validator(vt):
#     _t = validator_types.get(vt, None)
#     if _t is None:
#         raise KeyError('Not a valid validator')
#
#     class Validator(BaseModel):
#         value: str
#
#         @field_validator('value')
#         @classmethod
#         def call_validator(cls, value, info):
#             cls._vfunc(cls, value, info)
#
#     Validator._vfunc = _t
#
#     return Validator
#
# from typing_extensions import Annotated
# orcid = Annotated[str, get_validator('orcid')]
#
# class MyValidator(BaseModel):
#     name: str
#     id: orcid
#
#
# m = MyValidator(name='test', id='0000-0001-2345-678X')
# #
# # get_validator('orcid').model_validate(dict(value="0000-0001-2345-678X"),
# #                                       context={'parent': 1, 'attrs': {}})
