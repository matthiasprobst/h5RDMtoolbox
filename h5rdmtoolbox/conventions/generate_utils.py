import re
from itertools import count
from typing import List, Dict

regex_counter = count()


def get_regex_name():
    return f'regex_{next(regex_counter)}'


class RegexProcessor:
    """Process regex validator.

    Parameters
    ----------
    standard_attribute: Dict
        Standard attribute dictionary, e.g. {'validator': 'regex(r"^[a-zA-Z0-9_]*$")'}
    """
    def __init__(self, standard_attribute: Dict):
        regex_validator = get_regex_name()
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
        file.writelines(f'\ndef {self.name}(value, parent=None, attrs=None):')
        file.writelines(f"\n    pattern = re.compile(r'{self.re_pattern}')")
        file.writelines("\n    if not pattern.match(value):")
        file.writelines("\n        raise ValueError('Invalid format for pattern')")
        file.writelines("\n    return value")
        file.writelines(f"\n{self.name} = Annotated[int, WrapValidator({self.name})]\n")


def get_standard_attribute_class_lines(name, *, validator, description: str = None, **kwargs):
    validator_class_name = name.replace('-', '_')# + '_validator'
    validator = validator.strip('$')
    lines = [
        f'\nclass {validator_class_name}(BaseModel):',
        f'\n    """{description}"""',
        f'\n    value: {validator}\n',
    ]
    return lines


def get_validator_lines(name, values: Dict, description: str = None):
    validator_name = name.strip('$').replace('-', '_')
    lines = []
    lines.append(f'class {validator_name}(BaseModel):')
    if description is None:
        description = validator_name
    lines.append(f'\n    """{description}"""\n    ')
    lines.append('\n    '.join([f'{k}: {v}' for k, v in values.items()]))
    lines.append('\n\n')
    return lines


def get_enum_lines(name, values: List[str], description: str = None):
    """returns a list of lines for a enumerator validation class"""
    validator_name = name.strip('$').replace('-', '_')
    lines = []
    lines.append(f'class {validator_name}(str, Enum):\n')
    if description is None:
        description = ''
    lines.append(f'    """{description}"""\n')

    for enum_val in values:
        enum_split = enum_val.split(':', 1)
        if len(enum_split) == 1:
            enum_name, enum_value = enum_val, enum_val
        else:
            enum_name, enum_value = enum_split
        lines.append(f'    {enum_name} = "{enum_value}"\n')

    lines.append(f'\nclass {validator_name}(BaseModel):\n')
    lines.append(f'    value: {validator_name}\n')
    return lines


if __name__ == '__main__':
    for l in get_enum_lines('$test', ['a', 'b', 'c'], description='test'):
        print(l.strip('\n'))
