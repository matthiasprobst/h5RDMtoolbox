import re


class LongName(str):
    """Long Name class. Implements convention (rules) for usage"""
    MIN_LENGTH = 1
    PATTERN = ('^[0-9 ].*', 'Name must not start with a number or a space')

    def __new__(cls, value):
        # 1. Must be longer than MIN_LENGTH
        if len(value) < cls.MIN_LENGTH:
            raise ValueError(f'Name is too short. Must at least have {cls.MIN_LENGTH} character')
        # if value[0] == ' ':
        #     raise ValueError(f'Name must not start with a space')
        if re.match(cls.PATTERN[0], value):
            raise ValueError(cls.PATTERN[1])
        return str.__new__(cls, value)
