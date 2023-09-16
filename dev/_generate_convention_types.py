import yaml


def write_regex(name, pattern, target_filename):
    print(name, pattern)
    with open(target_filename, 'w') as f:
        func_name = name.strip('$')
        lines = f"""import re
from pydantic import (
    BaseModel,
)  

from validator_types import WrapValidator, Annotated


def _{func_name}(value, parent=None, attrs=None):
    pattern = re.compile(r"{pattern}")
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


{func_name} = Annotated[str, WrapValidator(_{func_name})]
"""
        f.writelines(lines)


def write_type(name, types, target_filename):
    if isinstance(types, dict):
        for k, v in types.items():
            if k == '$regex':
                write_regex(name, v, target_filename)


def convert(yaml_filename, target_filename):
    with open(yaml_filename, 'r') as f:
        data = yaml.safe_load(f)

    for k, v in data.items():
        if k.startswith('$') and 'long_name' in k:
            # it is a type definition
            write_type(k, v, target_filename)
        else:
            if k == 'long_name':
                print('its the standard attribute I was looking for')
                print(v)
                with open(target_filename, 'a') as f:
                    # write the validator class:
                    lines = f'\n\nclass {k.capitalize()}Validator(BaseModel):\n\t{k}: {v.get("validator").strip("$")}'
                    f.writelines(lines)


convert('new_convention.yaml', target_filename='new_convention_types.py')

from new_convention_types import Long_nameValidator

Long_nameValidator(long_name='As123')
