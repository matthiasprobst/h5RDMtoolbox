"""main"""
import pathlib
import shutil

convention_name = 'test_convention'
validation_yaml_filename = pathlib.Path(f'{convention_name}.yaml')

# create the convention directory where to build the validators
convention_dir = pathlib.Path(convention_name)
convention_dir.mkdir(parents=True, exist_ok=True)

vfunc_filename = convention_dir / 'convention.py'
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
from utils import get_specialtype_function_info

special_type_info = get_specialtype_function_info(vfunc_filename)
with open(convention_dir / f'convention.py', 'a') as f:
    f.writelines("""
    
from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

""")
with open(convention_dir / f'convention.py', 'a') as f:
    # write type definitions from YAML file:
    f.writelines('\n# ---- generated code: ----\n')
    for k, v in special_type_info.items():
        # lines = f"""\n\n{k} | {v} | unit = Annotated[str, WrapValidator(validate_units)]\n\n"""
        lines = f"""{k.strip('validate_')} = Annotated[str, WrapValidator({k})]\n"""
        f.writelines(lines)

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
            if 'regex' in v['validator']:
                import re

                regex_validator = 'regex_00'  # TODO use proper id
                match = re.search(r'regex\((.*?)\)', v['validator'])
                re_pattern = match.group(1)
                standard_attributes[k] = regex_validator
                _v = v.copy()
                _v['validator'] = regex_validator
                standard_attributes[k] = _v
                with open(convention_dir / f'convention.py', 'a') as f:
                    f.writelines(f"""import re\n\ndef {regex_validator}_validator(value, parent=None, attrs=None):
    pattern = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


{regex_validator} = Annotated[int, WrapValidator({regex_validator}_regex_validator)]""")
            else:
                standard_attributes[k] = v

# get validator and write them to convention-python file:
with open(convention_dir / f'convention.py', 'a') as f:
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

        _type_str = _type.strip("$")
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
