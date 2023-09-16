"""main"""
import pathlib
import shutil

convention_name = 'test_convention'
validation_yaml_filename = pathlib.Path(f'{convention_name}.yaml')

# create the convention directory where to build the validators
convention_dir = pathlib.Path(convention_name)
convention_dir.mkdir(parents=True, exist_ok=True)

vfunc_filename = convention_dir / 'special_type_funcs.py'
shutil.copy(f'{convention_name}_vfuncs.py', vfunc_filename)

# special validator functions are defined in the test_convention_vfuncs.py file
# read it and create the validator classes:

# with open(vfunc_filename, 'a') as f:
#     lines = ['\nfrom typing_extensions import Annotated',
#              '\nfrom pydantic.functional_validators import WrapValidator']
#     f.writelines(lines)
# f.write(f'from {convention_name} import special_type_funcs')
# f.write('\nfrom pydantic import BaseModel')

# testing:

#
# class MyValidator(BaseModel):
#     name: str
#     units: units
#
#
# MyValidator(name='hallo', units='km')

import yaml

# read the yaml file:
with open(validation_yaml_filename, 'r') as f:
    convention_dict = yaml.safe_load(f)

standard_attributes = {}
type_definitions = {}
for k, v in convention_dict.items():
    if isinstance(v, dict):
        # can be a type definition or a validator
        if k.startswith('$'):
            print(k, v)
            # it is a type definition
            # if it is a dict of entries, it is something like this:
            # class User(BaseModel):
            #     name: str
            #     personal_details: PersonalDetails
            if isinstance(v, dict):
                type_definitions[k] = v

        else:
            standard_attributes[k] = v

# get validator and write them to convention-python file:
with open(convention_dir / f'convention.py', 'w') as f:
    lines = """import inspect
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
"""

    # write imports to file:
    f.writelines(lines)

    # write type definitions from YAML file:
    for k, v in type_definitions.items():
        lines = f"""
        
class {k.strip('$').capitalize()}Validator(BaseModel):
    """ + '\n    '.join([f'{k}: {v}' for k, v in v.items()])
        # write imports to file:
    f.writelines(lines)

    for stda_name, stda in standard_attributes.items():
        validator_class_name = stda_name.capitalize() + 'Validator'
        _type = stda["validator"]
        if _type in type_definitions:
            continue
        if _type.strip("$") in ('str', 'int', 'float'):
            _type_str = _type.strip("$")
        else:
            _type_str = f'get_special_type("{_type.strip("$")}")'
        lines = [
            # testing:
            # f'\nprint(special_type_funcs.units("123", None, None))'
            f'\n\n\nclass {validator_class_name}(BaseModel):',
            f'\n    """{stda["description"]}"""',
            f'\n    value: {_type_str}',
            # f'\n\n{validator_class_name}(value="hallo")'

        ]
        f.writelines(lines)
    f.writelines('\n\n\n')
    f.writelines('UnitsValidator(value="1")\n')
