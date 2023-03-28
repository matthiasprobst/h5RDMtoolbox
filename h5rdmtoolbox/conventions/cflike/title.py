import re

from .errors import TitleError
from ..registration import StandardAttribute


class TitleAttribute(StandardAttribute):
    """Title attribute"""

    name = 'title'

    def setter(self, obj, value):
        """Set title"""
        if value[0] == ' ':
            raise TitleError('Title must not start with a space')
        if value[-1] == ' ':
            raise TitleError('Title must not end with a space')
        if re.match('^[0-9 ].*', value):
            raise TitleError('Title must not start with a number')
        obj.attrs.create(self.name, value)

