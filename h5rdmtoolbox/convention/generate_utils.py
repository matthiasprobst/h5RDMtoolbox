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
        file.writelines(f"\n{self.name} = Annotated[str, WrapValidator({self.name})]\n")


