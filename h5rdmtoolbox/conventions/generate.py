"""main"""
import pathlib
import shutil
import yaml

from h5rdmtoolbox._user import UserDir


def write_convention_module_from_yaml(yaml_filename: pathlib.Path):
    yaml_filename = pathlib.Path(yaml_filename)
    convention_name = yaml_filename.stem

    print(f'Convention "{convention_name}" filename: {yaml_filename}')

    print('creating directory for the convention')
    # create the convention directory where to build the validators
    convention_dir = UserDir.user_dirs['conventions'] / convention_name
    convention_dir.mkdir(parents=True, exist_ok=True)

    target_convention_filename = convention_dir / 'convention.py'

    special_validator_filename = yaml_filename.parent / f'{convention_name}_vfuncs.py'
    if special_validator_filename.exists():
        print(f'Found special functions file: {special_validator_filename}')
        shutil.copy(special_validator_filename, target_convention_filename)
    else:
        print('No special functions defined')
        # touch file:
        with open(convention_dir / f'convention.py', 'w'):
            pass

    validator_dict = {}

    # special validator functions are defined in the test_convention_vfuncs.py file
    # read it and create the validator classes:

    special_type_info = get_specialtype_function_info(target_convention_filename)
    with open(convention_dir / f'convention.py', 'a') as f:
        f.writelines('\n# ---- generated code: ----\nfrom h5rdmtoolbox.conventions.toolbox_validators import *\n')
        f.writelines("""

from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

""")
    with open(convention_dir / f'convention.py', 'a') as f:
        # write type definitions from YAML file:
        for k, v in special_type_info.items():
            lines = f"""{k.strip('validate_')} = Annotated[str, WrapValidator({k})]\n"""
            f.writelines(lines)

    # read the yaml file:
    with open(yaml_filename, 'r') as f:
        convention_dict = yaml.safe_load(f)

    standard_attributes = {}
    type_definitions = {}
    meta = {}
    for k, v in convention_dict.items():
        if isinstance(v, dict):
            # can be a type definition or a validator
            if k.startswith('$'):
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
                    _v['validator'] = f'{regex_validator}'
                    standard_attributes[k] = _v
                    with open(convention_dir / f'convention.py', 'a') as f:
                        f.writelines(f"""import re\n\ndef {regex_validator}_validator(value, parent=None, attrs=None):
    pattern = re.compile(r'{re_pattern}')
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


{regex_validator} = Annotated[int, WrapValidator({regex_validator}_validator)]""")
                else:
                    standard_attributes[k] = v
        else:
            meta[k.strip('_')] = v

    # get validator and write them to convention-python file:
    with open(convention_dir / f'convention.py', 'a') as f:
        # write type definitions from YAML file:
        lines = None
        for k, v in type_definitions.items():
            validator_name = k.strip('$').capitalize()
            validator_dict[k] = f'{validator_name}Validator'
            lines = f"""

class {validator_name}Validator(BaseModel):
    """ + '\n    '.join([f'{k}: {v}' for k, v in v.items()])
            # write imports to file:
        if lines:
            f.writelines(lines)

        for stda_name, stda in standard_attributes.items():
            validator_class_name = stda_name.capitalize() + 'Validator'
            _type = stda["validator"]
            if _type in type_definitions:
                continue

            _type_str = _type.strip("$")
            validator_dict[_type] = validator_class_name
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
        f.writelines('validator_dict = {\n    ')
        f.writelines('\n    '.join(f"'{k}': {v}," for k, v in validator_dict.items()))
        f.writelines("\n    '$int': IntValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n    '$str': StringValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n    '$float': FloatValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n}\n")
        # f.writelines(f'standard_attributes_dict = {standard_attributes}\n')

        f.writelines('\n')
        f.writelines(f'from h5rdmtoolbox.conventions.standard_attributes import StandardAttribute\n\n')
        f.writelines(f'from h5rdmtoolbox.conventions import Convention\n\n')
        f.writelines('standard_attributes = {\n    ')
        for k, v in standard_attributes.items():
            f.writelines(f"""    "{k}": StandardAttribute(
            name='{k}',
            description='{v.get('description', None)}',
            validator=validator_dict.get('{v.get('validator', None)}'),
            target_method='{v.get('target_method', None)}',
            default_value="{v.get('default_value', None)}",
    ),
""")
        f.writelines('}\n')
        f.writelines(f"""cv = Convention(
    name="{meta.get('name', None)}",        
    contact="{meta.get('contact', None)}",
    institution="{meta.get('institution', None)}",
    decoders="{meta.get('decoders', None)}",
    standard_attributes=standard_attributes
)
cv.register()
""")

        # _standard_attributes = standard_attributes.copy()
        # for k, v in standard_attributes.items():
        #     _standard_attributes[k]['validator'] = validator_dict.get(v['validator'], None)
        #     if _standard_attributes[k]['validator'] is None:
        #         print(f'could not find validator for {k}: {v["validator"]}')
        # f.writelines(f'standard_attributes_dict = {_standard_attributes}\n')
        # f.writelines(
        #     f'standard_attributes = {{StandardAttributes(k, **v) for k, v in standard_attributes_dict.items()}}\n')


# UTILITIES:
import ast
import warnings


def extract_function_info(node):
    function_info = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            function_name = item.name
            arguments = [arg.arg for arg in item.args.args]
            function_info.append((function_name, arguments))
    return function_info


def scan_python_file(file_path):
    with open(file_path, "r") as file:
        source_code = file.read()

    try:
        tree = ast.parse(source_code)
        function_info = extract_function_info(tree)
        return function_info
    except SyntaxError as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def validate_specialtype_functions(specialtype_functions):
    for k, v in specialtype_functions.items():
        if not k.startswith('validate_'):
            raise ValueError(f'Function name must start with "validate_": {k}')
        if not len(v) == 3:
            raise ValueError(f'Function must have 3 arguments: {k}')


def get_specialtype_function_info(file_path, validate=True):
    function_info = scan_python_file(file_path)

    function_info_dict = {}

    if function_info:
        print("Function info found:")
        for name, arguments in function_info:
            if name.startswith("validate_"):
                function_info_dict[name] = arguments
            else:
                warnings.warn(f'Skipping function "{name}" in {file_path} because it does not start with "validate_"')
    print(f'Found {len(function_info_dict)} function(s) in {file_path}')
    if validate:
        validate_specialtype_functions(function_info_dict)
    return function_info_dict


if __name__ == '__main__':
    write_convention_module_from_yaml('test_convention.yaml')
