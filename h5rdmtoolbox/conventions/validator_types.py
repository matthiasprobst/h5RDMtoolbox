import re
from pydantic.functional_validators import WrapValidator
from typing_extensions import Annotated


def validate_orcid_format(value, parent=None, attrs=None):
    # Define the ORCID regular expression pattern
    orcid_pattern = re.compile(r'^\d{4}-\d{4}-\d{4}-\d{3}(\d|X)$')

    # Check if the value matches the pattern
    if not orcid_pattern.match(value):
        raise ValueError('Invalid ORCID format')

    # Check if the checksum is valid
    digits = [int(digit) if digit != 'X' else 10 for digit in value.replace('-', '')]
    total = sum((i + 1) * digit for i, digit in enumerate(digits))
    if total % 11 != 0:
        raise ValueError('Invalid ORCID checksum')

    return value


validator_types = {'orcid': Annotated[int, WrapValidator(validate_orcid_format)],
                   'str': str}
