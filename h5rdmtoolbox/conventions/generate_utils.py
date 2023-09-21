from typing import List, Dict


def get_validator_lines(name, values: Dict, description: str = None):
    validator_name = name.strip('$').replace('-', '_')
    lines = []
    lines.append(f'class {validator_name}_validator(BaseModel):')
    if description is None:
        description = ''
    lines.append(f'    """{description}"""\n')
    lines.append('\n    '.join([f'{k}: {v}' for k, v in values.items()]))
    return lines


def get_enum_lines(name, values: List[str], description: str = None, write_import: bool = True):
    """returns a list of lines for a enumerator validation class"""
    validator_name = name.strip('$').replace('-', '_')
    lines = []
    if write_import:
        lines.append(f'\nfrom enum import Enum\n\n')
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

    lines.append(f'\nclass {validator_name}_validator(BaseModel):\n')
    lines.append(f'    value: {validator_name}\n')
    return lines


if __name__ == '__main__':
    for l in get_enum_lines('$test', ['a', 'b', 'c'], description='test'):
        print(l.strip('\n'))
