import re

from . import StandardAttributeValidator


class MinLengthValidator(StandardAttributeValidator):

    def __call__(self, value, parent):
        if len(value) < self.ref:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.ref}')
        return value


class MaxLengthValidator(StandardAttributeValidator):

    def __call__(self, value, parent):
        if len(value) > self.ref:
            raise ValueError(f'The value "{value}" is shorter than the minimum length {self.ref}')
        return value


class RegexValidator(StandardAttributeValidator):

    def __call__(self, value, parent):
        if re.match(self.ref, value) is None:
            raise ValueError(f'The value "{value}" does not match the pattern "{self.ref}"')
        return value
