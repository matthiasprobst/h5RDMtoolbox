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


if __name__ == "__main__":
    validate_specialtype_functions(get_specialtype_function_info("_test_convention_vfuncs.py"))
