"""main"""
import pathlib
import re
import shutil
import yaml
from typing import List, Callable
from typing import Union, Dict

from h5rdmtoolbox._user import UserDir


def write_convention_module_from_yaml(yaml_filename: pathlib.Path, name=None):
    """Generate the convention.py in the user directory from a YAML file"""
    yaml_filename = pathlib.Path(yaml_filename)
    if name is None:
        convention_name = yaml_filename.stem
    else:
        convention_name = name

    print(f'Convention "{convention_name}" filename: {yaml_filename}')

    print('creating directory for the convention')
    # create the convention directory where to build the validators

    convention_name = convention_name.lower().replace("-", "_")

    convention_dir = UserDir.user_dirs['conventions'] / convention_name
    convention_dir.mkdir(parents=True, exist_ok=True)

    py_filename = convention_dir / f'{convention_name}.py'

    special_validator_filename = yaml_filename.parent / f'{convention_name}_vfuncs.py'
    if special_validator_filename.exists():
        print(f'Found special functions file: {special_validator_filename}')
        shutil.copy(special_validator_filename, py_filename)
    else:
        print('No special functions defined')
        # touch file:
        with open(py_filename, 'w'):
            pass

    # for reference, also copy the yaml file there:
    print(f'DEBUG DEBUG copying yaml file to convention directory: {yaml_filename} -> {convention_dir}')
    shutil.copy2(yaml_filename, convention_dir / f'{convention_name}.yaml')

    validator_dict = {}

    # special validator functions are defined in the test_convention_vfuncs.py file
    # read it and create the validator classes:

    special_type_info = get_specialtype_function_info(py_filename)
    with open(py_filename, 'a') as f:
        f.writelines('\n# ---- generated code: ----\nfrom h5rdmtoolbox.conventions.toolbox_validators import *\n')
        f.writelines("""

from pydantic import BaseModel
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated

""")
    with open(py_filename, 'a') as f:
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
    imports = []
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
                    regex_validator = get_regex_name()  # TODO use proper id
                    match = re.search(r'regex\((.*?)\)', v['validator'])
                    re_pattern = match.group(1)
                    if re_pattern.startswith("r'") and re_pattern.endswith("'"):
                        re_pattern = re_pattern[2:-1]
                        standard_attributes[k] = regex_validator
                    _v = v.copy()
                    _v['validator'] = f'{regex_validator}'
                    standard_attributes[k] = _v

                    with open(py_filename, 'a') as f:
                        if 're' not in imports:
                            f.writelines('import re\n')
                            imports.append('re')
                        f.writelines(f"""

def {regex_validator}_validator(value, parent=None, attrs=None):
    pattern = re.compile(r'{re_pattern}')
    if not pattern.match(value):
        raise ValueError('Invalid format for pattern')
    return value


{regex_validator} = Annotated[int, WrapValidator({regex_validator}_validator)]""")
                else:
                    standard_attributes[k] = v
        elif isinstance(v, str):
            meta[k.strip('_')] = v
        elif isinstance(v, list):
            # is an enum
            type_definitions[k] = v
        else:
            raise KeyError(f'Unknown type for key {k}: {type(v)}')

    # get validator and write them to convention-python file:
    with open(py_filename, 'a') as f:
        # write type definitions from YAML file:
        for k, v in type_definitions.items():
            validator_name = k.strip('$').replace('-', '_')
            validator_dict[k] = f'{validator_name}_validator'
            if isinstance(v, list):
                # create_enum_class(k, v, f)
                lines = f"""
from enum import Enum

class {validator_name}(str, Enum):
"""
                for enum_val in v:
                    enum_split = enum_val.split(':', 1)
                    if len(enum_split) == 1:
                        enum_name, enum_value = enum_val, enum_val
                    else:
                        enum_name, enum_value = enum_split
                    lines += f'    {enum_name} = "{enum_value}"\n'
                lines += f"""

class {validator_name}_validator(BaseModel):
    value: {validator_name}

"""
            else:
                lines = f"""

class {validator_name}_validator(BaseModel):
    """ + '\n    '.join([f'{k}: {v}' for k, v in v.items()])
                # write imports to file:
            if lines:
                f.writelines(lines)

        for stda_name, stda in standard_attributes.items():
            validator_class_name = stda_name.replace('-', '_') + '_validator'
            _type = stda["validator"]
            if isinstance(_type, dict):
                raise TypeError('A validator cannot be a dict but need to specify a validator type, like "$str". '
                                'If you want to provide a default value, do it using the entry "default_value".')
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

        f.writelines('validator_dict = {\n    ')
        f.writelines('\n    '.join(f"'{k}': {v}," for k, v in validator_dict.items()))
        f.writelines("\n    '$int': IntValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n    '$str': StringValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n    '$float': FloatValidator,  # see h5rdmtoolbox.conventions.toolbox_validators")
        f.writelines("\n}\n")
        # f.writelines(f'standard_attributes_dict = {standard_attributes}\n')

        f.writelines('\n')
        f.writelines(f'from h5rdmtoolbox.conventions import Convention, standard_attributes, logger\n\n')
        f.writelines('standard_attributes = {\n    ')
        for kk, vv in standard_attributes.items():
            _default_value = _process_paths(vv.get('default_value', None), relative_to=yaml_filename.parent)
            if _default_value is None:
                _default_value_str = 'None'
            elif isinstance(_default_value, str):
                if _default_value.startswith('r"'):
                    _default_value_str = f"{_default_value}"
                else:
                    _default_value_str = f"'{_default_value}'"
            f.writelines(f"""    "{kk}": standard_attributes.StandardAttribute(
        name='{kk}',
        description={_str_getter(vv, 'description', None)},
        validator=validator_dict.get({_str_getter(vv, 'validator', None)}),
        target_method={_str_getter(vv, 'target_method', None)},
        default_value={_default_value_str},
        requirements={_str_getter(vv, 'requirements', None)},
),
""")
        f.writelines('}\n')
        f.writelines(f"""cv = Convention(
    name={_str_getter(meta, 'name', None)},
    contact={_str_getter(meta, 'contact', None)},
    institution={_str_getter(meta, 'institution', None)},
    decoders={_str_getter(meta, 'decoders', None)},
    standard_attributes=standard_attributes
)
logger.debug(f'Registering convention {{cv.name}}')
cv.register()
""")


# UTILITIES:
import ast
import warnings
from itertools import count

regex_counter = count()


def get_regex_name():
    return f'regex_{next(regex_counter)}'


def _str_getter(_dict, key, default=None) -> str:
    val = _dict.get(key, default)
    if val is None:
        return 'None'
    if isinstance(val, str):
        return f'"{val}"'
    return f'{val}'


def extract_function_info(func: Callable) -> List:
    """Extract function name and arguments from a function."""
    function_info = []
    for item in func.body:
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


def _process_relpath(rel_filename, relative_to) -> str:
    return f'r"{pathlib.Path((relative_to / rel_filename).absolute())}"'


def _process_paths(data: Union[Dict, str], relative_to) -> Union[str, List[str], Dict[str, str]]:
    # processed_data = {}
    if data is None:
        return data
    if isinstance(data, str):
        match = re.search(r'relpath\((.*?)\)', data)
        if match:
            return _process_relpath(match.group(1), relative_to)
        return data
    elif isinstance(data, list):
        return [_process_paths(item, relative_to) for item in data]
    elif isinstance(data, dict):
        _data = data.copy()
        for key, value in data.items():
            if isinstance(value, str):
                match = re.search(r'relpath\((.*?)\)', value)
                if match:
                    _data[key] = _process_relpath(match.group(1), relative_to)
            elif isinstance(value, list):
                _data[key] = [_process_paths(item, relative_to) for item in value]
            elif isinstance(value, dict):
                _data[key] = _process_paths(_data[key], relative_to)
        return _data
    return data


if __name__ == '__main__':
    write_convention_module_from_yaml('test_convention.yaml')
