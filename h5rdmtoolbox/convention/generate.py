"""Module to generate a convention Python file from a YAML file"""
import ast
import logging
import pathlib
import re
import shutil
import warnings
import yaml
from itertools import count
from typing import Dict
from typing import List, Union

from h5rdmtoolbox.user import UserDir
from h5rdmtoolbox.convention import toolbox_validators

logger = logging.getLogger('h5rdmtoolbox')

regex_counter = count()

INDENT = '    '


def write_convention_module_from_yaml(yaml_filename: pathlib.Path, name=None):
    """Generates a python file based on the inputted yaml file.
    The convention python file is written to the directory `UserDir.user_dirs['convention']`.

    Parameters
    ----------
    yaml_filename: pathlib.Path
        The convention YAML file
    name: str, optional
        The name of the convention. If not given, the name is taken from the filename (stem of the file).
    """
    yaml_filename = pathlib.Path(yaml_filename)
    if name is None:
        convention_name = yaml_filename.stem
    else:
        convention_name = name
    logger.debug('Writing convention module from YAML file "%s". Name of convention: "%s"',
                 yaml_filename, convention_name)
    # create the convention directory where to build the validators

    convention_name = convention_name.lower().replace("-", "_")

    convention_dir = UserDir.user_dirs['convention'] / convention_name
    convention_dir.mkdir(parents=True, exist_ok=True)
    logger.debug('Convention directory: "%s"', convention_dir)

    py_filename = convention_dir / f'{convention_name}.py'
    logger.debug('Convention python file: "%s"', py_filename)

    # Some validators are quite complex and need some programming knowledge.
    # While a YAML or JSON convention files is easy to read and write and can be
    # edited by regular users, conditional validators, such as "units", which
    # requires to call a validator function, cannot be expressed in YAML or JSON
    # and therefore need to be written in Python. The h5rdmtoolbox provides a
    # set of validator functions in separate files within the "validator library"
    # However, the user may also provide their own validator functions. These
    # functions are stored in a separate file, which is named
    # <convention_name>_vfuncs.py (vfuncs stands for "validator functions").
    # If such a file exists, it is copied to the convention directory.
    # If not, an empty file is created.
    user_validator_functions = yaml_filename.parent / f'{yaml_filename.stem}_vfuncs.py'
    if user_validator_functions.exists():
        logger.debug('A validator function file for the convention exists: "%s". Copying it to "%s"',
                     user_validator_functions, py_filename)
        shutil.copy(user_validator_functions, py_filename)

        # reading the user validator functions file and extract the information
        user_defined_validator_info = get_user_define_validator_info(py_filename)
    else:
        # touch file:
        logger.debug('No validator function file for the convention exists. Creating an empty file "%s"', py_filename)
        user_defined_validator_info = {}
        with open(py_filename, 'w'):
            pass

    # for reference, also copy the yaml file there:
    logger.debug('Copying the YAML file "%s" to "%s"', yaml_filename, convention_dir)
    shutil.copy2(yaml_filename, convention_dir / f'{convention_name}.yaml')

    with open(py_filename, 'a') as f:
        f.writelines('\n# ---- generated code: ----\nfrom h5rdmtoolbox.convention import toolbox_validators\n')
        f.writelines('\nfrom pydantic import BaseModel\n')
        f.writelines('from pydantic.functional_validators import WrapValidator\n')
        f.writelines('from typing_extensions import Annotated\n\n')
        f.writelines('from typing import *\n\n')

        # write special type definitions:
        logger.debug('Writing user-defined validators to "%s"', py_filename)
        for k, v in user_defined_validator_info.items():
            lines = f"""{k.strip('validate_')} = Annotated[str, WrapValidator({k})]\n"""
            f.writelines(lines)

    # read the yaml file:
    logger.debug('Reading YAML file "%s"', yaml_filename)
    with open(yaml_filename, 'r') as f:
        convention_dict = yaml.safe_load(f)

    # First extract the meta information:
    metadata = {k.strip('_'): v for k, v in convention_dict.items() if k.startswith('__') and k.endswith('__')}
    # standard_attributes:
    standard_attributes = {k: v for k, v in convention_dict.items() if isinstance(v, dict) and not k.startswith('$')}
    # one special case: validator is a regex expression:
    for k in standard_attributes.keys():
        validator = standard_attributes[k]['validator']
        if 'regex' in validator:
            _regex_proc = RegexProcessor(standard_attributes[k])
            standard_attributes[k] = _regex_proc.get_dict()
            with open(py_filename, 'a') as f:
                _regex_proc.write_lines(f)
        elif validator.startswith('$'):
            standard_attributes[k]['validator'] = validator

    class_definitions = {k: v for k, v in convention_dict.items() if isinstance(v, dict) and k.startswith('$')}
    literal_definition = {k: v for k, v in convention_dict.items() if isinstance(v, list) and k.startswith('$')}
    used_toolbox_validators = {}
    auto_created_classes = {}

    # first write literals
    with open(py_filename, 'a') as f:
        f.write('from typing_extensions import Literal\n')
        for k, v in literal_definition.items():
            _literal_values = [f'\n{INDENT}"{x}"' if isinstance(x, str) else str(x) for x in v]
            f.write(f'\n{k[1:]} = Literal[{", ".join(_literal_values)}\n]\n')
            # f.write(f'{k} = Literal[{", ".join(v)}]\n')

        # write base classes
        for k, v in class_definitions.items():
            f.write(f'\nclass {k[1:]}(BaseModel):')
            description = v.get('description', k[1:])
            f.write(f'\n{INDENT}"""{description}"""\n')
            validator = {}
            _validator_default = {}
            for kk, vv in v.items():
                # _vv = vv.strip('$')
                splitted_validator = vv.strip('$').split('=', 1)
                validator_name = splitted_validator[0].strip()
                if len(splitted_validator) == 2:
                    default_value = splitted_validator[1].strip()
                else:
                    default_value = None
                _validator_default[kk] = [validator_name, default_value]

                if validator_name in toolbox_validators.validators:

                    try:
                        if toolbox_validators.validators[
                            validator_name].__name__ != 'Annotated':  # in py3.8 this will raise an error
                            validator[
                                kk] = f'toolbox_validators.{toolbox_validators.validators[validator_name].__name__}'
                            used_toolbox_validators[
                                validator_name] = f'toolbox_validators.{toolbox_validators.validators[validator_name].__name__}'
                        else:
                            validator[kk] = f'toolbox_validators.validators["{validator_name}"]'
                            used_toolbox_validators[
                                validator_name] = f'toolbox_validators.validators["{validator_name}"]'

                    except AttributeError:
                        validator[kk] = f'toolbox_validators.validators["{validator_name}"]'
                        used_toolbox_validators[validator_name] = f'toolbox_validators.validators["{validator_name}"]'
                else:
                    validator[kk] = vv
            for ak, av in validator.items():
                validator_value, validator_default = _validator_default[ak]
                if validator_default is not None:
                    f.write(
                        f'{INDENT}{ak}: {used_toolbox_validators.get(validator_name, validator_value)} = {validator_default}\n')
                else:
                    f.write(f'{INDENT}{ak}: {av}\n')
            # f.write(f'\n{INDENT}'.join([f'{ak}: {av}' for ak, av in validator.items()]))
            f.write('\n\n')

        # write standard attribute classes:
        for k, v in standard_attributes.items():
            _validator = v.get('validator', None)
            if not _validator:
                raise KeyError(f'No validator for {k}')
            if _validator.startswith('$'):
                _validator = _validator[1:]
            if _validator in toolbox_validators.validators:
                # don't create a base class
                try:
                    if toolbox_validators.validators[
                        _validator].__name__ != 'Annotated':  # in py3.8 this will raise an error
                        used_toolbox_validators[
                            f'${_validator}'] = f'toolbox_validators.{toolbox_validators.validators[_validator].__name__}'
                    else:
                        used_toolbox_validators[f'${_validator}'] = f'toolbox_validators.validators["{_validator}"]'
                except AttributeError:
                    used_toolbox_validators[f'${_validator}'] = f'toolbox_validators.validators["{_validator}"]'
                continue
            _default_value = v.get('default_value', '$EMPTY')

            # it is not allowed to have a dash in the class name.
            # However, it was needed to have standard attribute with the same name for different methods
            class_name = k.replace('-', '_')
            attr_name = k.rsplit('-', 1)[0]
            f.write(f'\nclass {class_name}(BaseModel):')
            description = v.get('description', k)
            f.write(f'\n{INDENT}"""{description}"""')
            f.write(f'\n{INDENT}{attr_name}: {_validator}')
            # f.write(f'\n{INDENT}default_value: "{_default_value}"')
            # f.write(f'\n{INDENT}description: "{description}"\n{INDENT}')
            # f.write('\n\t'.join([f'{ak}: {av}' for ak, av in v.items()]))
            f.write('\n\n')
            auto_created_classes[_validator] = k

        # with open(py_filename, 'a') as f:
        f.write('\nvalidator_dict = {\n' + INDENT)
        f.write(f'\n{INDENT}'.join(f"\n'{k}': {k[1:]}," for k, v in class_definitions.items()))
        f.write(f'\n{INDENT}'.join(f"'{k}': {v}," for k, v in used_toolbox_validators.items()))
        f.write("\n}\n")

        f.write('\n')
        f.write('from h5rdmtoolbox.convention import Convention, standard_attributes\n')
        f.write('import logging\n')
        f.write('logger = logging.getLogger("h5rdmtoolbox")\n\n')
        f.write('generated_standard_attributes = {\n')

    with open(py_filename, 'a') as f:
        for kk, vv in standard_attributes.items():
            _default_value = _process_paths(vv.get('default_value', None), relative_to=yaml_filename.parent)
            if _default_value is None:
                _default_value_str = 'None'
            elif isinstance(_default_value, str):
                if _default_value.startswith('r"'):
                    _default_value_str = f"{_default_value}"
                else:
                    _default_value_str = f"'{_default_value}'"

            validator = vv['validator']
            if validator in used_toolbox_validators:
                _validator = used_toolbox_validators[validator]
            elif validator.strip('$') in auto_created_classes:
                _validator = f"{auto_created_classes[validator.strip('$')]}"
            elif kk in standard_attributes:
                _validator = f"{validator[1:]}"

            f.writelines(f"""{INDENT}"{kk}": standard_attributes.StandardAttribute(
        name='{kk}',
        description={_str_getter(vv, 'description', None)},
        validator={_validator.replace('-', '_')},
        alternative_standard_attribute={_str_getter(vv, 'alternative_standard_attribute', None)},
        rdf_predicate={_str_getter(vv, 'rdf_predicate', None)},
        frdf_predicate={_str_getter(vv, 'frdf_predicate', None)},
        target_method={_str_getter(vv, 'target_method')},
        default_value={_default_value_str},
        requirements={_str_getter(vv, 'requirements', None)},
{INDENT}),
""")
        f.writelines('}\n')
        f.writelines(f"""cv = Convention(
    name={_str_getter(metadata, 'name', None)},
    contact={_str_getter(metadata, 'contact', None)},
    institution={_str_getter(metadata, 'institution', None)},
    decoders={_str_getter(metadata, 'decoders', None)},
    standard_attributes=generated_standard_attributes
)
logger.debug(f'Registering convention "{{cv.name}}"')
cv.register()
""")


def _str_getter(_dict, key, default=None) -> str:
    val = _dict.get(key, default)
    if val is None:
        return 'None'
    if isinstance(val, str):
        return f'"{val}"'
    return f'{val}'


def extract_function_info(node) -> List:
    """Extract function name and arguments from a function."""
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
        return []


def validate_specialtype_functions(specialtype_functions):
    for k, v in specialtype_functions.items():
        if not k.startswith('validate_'):
            raise ValueError(f'Function name must start with "validate_": {k}')
        if not len(v) == 3:
            raise ValueError(f'Function must have 3 arguments: {k}')


def get_user_define_validator_info(file_path, validate=True):
    """Reading the user-defined validator functions from a python file."""
    function_info = scan_python_file(file_path)

    function_info_dict = {}

    if function_info:
        for name, arguments in function_info:
            if name.startswith("validate_"):
                function_info_dict[name] = arguments
            # else:
            #     warnings.warn(f'Skipping function "{name}" in {file_path} because it does not start with "validate_"')
    if validate:
        validate_specialtype_functions(function_info_dict)
    return function_info_dict


def _process_relpath(rel_filename, relative_to) -> str:
    return f'r"{pathlib.Path((relative_to / rel_filename).absolute())}"'


def _process_paths(paths: Union[Dict, str], relative_to) -> Union[str, List[str], Dict[str, str]]:
    if paths is None:
        return paths
    if isinstance(paths, str):
        match = re.search(r'relpath\((.*?)\)', paths)
        if match:
            return _process_relpath(match.group(1), relative_to)
        return paths
    elif isinstance(paths, list):
        return [_process_paths(item, relative_to) for item in paths]
    elif isinstance(paths, dict):
        _paths = paths.copy()
        for key, value in paths.items():
            if isinstance(value, str):
                match = re.search(r'relpath\((.*?)\)', value)
                if match:
                    _paths[key] = _process_relpath(match.group(1), relative_to)
            elif isinstance(value, list):
                _paths[key] = [_process_paths(item, relative_to) for item in value]
            elif isinstance(value, dict):
                _paths[key] = _process_paths(_paths[key], relative_to)
        return _paths
    return paths


class RegexProcessor:
    """Process regex validator.

    Parameters
    ----------
    standard_attribute: Dict
        Standard attribute dictionary, e.g. {'validator': 'regex(r"^[a-zA-Z0-9_]*$")'}
    """

    def __init__(self, standard_attribute: Dict):
        regex_validator = f'regex_{next(regex_counter)}'
        validator = standard_attribute['validator']
        self.name = regex_validator
        re_pattern = validator.split('regex(', 1)[1].rsplit(')', 1)[0]
        # match = re.search(r'regex\((.*?)\)', validator)
        # re_pattern = match.group(1)

        self.standard_attribute = standard_attribute.copy()
        if re_pattern.startswith("r'") and re_pattern.endswith("'"):
            re_pattern = re_pattern[2:-1]
        self.standard_attribute['validator'] = f'{regex_validator}'
        self.re_pattern = re_pattern

    def get_dict(self):
        return self.standard_attribute

    def write_lines(self, file):
        """Write validator lines to file"""
        file.writelines(f'\n\nimport re\n\n')
        file.writelines(f'\ndef {self.name}(value, handler):')
        file.writelines(f"\n    pattern = re.compile(r'{self.re_pattern}')")
        file.writelines("\n    if not pattern.match(value):")
        file.writelines("\n        raise ValueError('Invalid format for pattern')")
        file.writelines("\n    return value")
        file.writelines(f"\n{self.name} = Annotated[str, WrapValidator({self.name})]\n")
