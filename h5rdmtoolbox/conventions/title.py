import re

from .standard_attribute import StandardAttribute


class TitleError(ValueError):
    """An error associated with the title property"""


class TitleAttribute(StandardAttribute):
    """Title attribute"""

    name = 'title'

    def set(self, value):
        """Set title"""
        if value[0] == ' ':
            raise TitleError('Title must not start with a space')
        if value[-1] == ' ':
            raise TitleError('Title must not end with a space')
        if re.match('^[0-9 ].*', value):
            raise TitleError('Title must not start with a number')
        super().set(value)
