import re

from .errors import TitleError
from ..registration import AbstractUserAttribute


class TitleAttribute(AbstractUserAttribute):
    """Title attribute"""

    def set(self, value):
        """Set title"""
        if value[0] == ' ':
            raise TitleError('Title must not start with a space')
        if value[-1] == ' ':
            raise TitleError('Title must not end with a space')
        if re.match('^[0-9 ].*', value):
            raise TitleError('Title must not start with a number')
        self.attrs.create('title', value)

    def get(self):
        """Get title attribute"""
        return TitleAttribute.parse(self.attrs.get('title', None))

    def delete(self):
        """Delete title attribute"""
        self.attrs.__delitem__('title')
