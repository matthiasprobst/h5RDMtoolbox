import re

from .errors import LongNameError


class LongName(str):
    """Long Name class. Implements convention (rules) for usage"""
    MIN_LENGTH = 1
    PATTERN = '^[0-9 ].*'

    def __new__(cls, value):
        # 1. Must be longer than MIN_LENGTH
        if len(value) < cls.MIN_LENGTH:
            raise LongNameError(f'Name is too short. Must at least have {cls.MIN_LENGTH} character')
        if re.match(cls.PATTERN, value):
            raise LongNameError(f'Name must not start with a number or a space: "{value}"')
        return str.__new__(cls, value)


class LongOrStandardNameWarning(Warning):
    """Warning raised if neither a long_name nor a standard_names was passed during dataset creation"""

    def __init__(self, dataset_name):
        self.message = f'No long_name or standard_name given for dataset "{dataset_name}".\n' \
                       f' It is highly recommended to give either of it otherwise file check will fail.'

    def __str__(self):
        return repr(self.message)
