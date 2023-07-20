import re

from .base import StandardAttributeValidator


class RegexValidator(StandardAttributeValidator):

    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, value, parent, **kwargs) -> bool:
        return re.match(self.pattern, value) is not None
