import re

from .base import StandardAttributeValidator


class MinLengthValidator(StandardAttributeValidator):

    def __init__(self, minlength):
        self.minlength = minlength

    def __call__(self, value, parent):
        if len(value) < self.minlength:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.minlength}')
        return value


class MaxLengthValidator(StandardAttributeValidator):

    def __init__(self, maxlength):
        self.maxlength = maxlength

    def __call__(self, value, parent):
        if len(value) > self.maxlength:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.maxlength}')
        return value


class RegexValidator(StandardAttributeValidator):

    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, value, parent):
        if re.match(self.pattern, value) is None:
            raise ValueError(f'The value "{value}" does not match the pattern "{self.pattern}"')
        return value
