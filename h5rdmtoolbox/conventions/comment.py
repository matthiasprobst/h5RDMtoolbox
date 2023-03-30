import re
from typing import Union

from .standard_attribute import StandardAttribute


class CommentError(ValueError):
    """An error associated with the comment property"""


class Comment(str):
    """Comment class. Implements convention (rules) for usage"""
    MIN_LENGTH = 1
    MAX_LENGTH = 300  # arbitrary, seems reasonable...
    PATTERN = '^[0-9 ].*'

    name = 'comment'

    def __new__(cls, value):
        # 1. Must be longer than MIN_LENGTH
        if len(value) < cls.MIN_LENGTH:
            raise CommentError(f'Name is too short. Must at least have {cls.MIN_LENGTH} character')
        if cls.MAX_LENGTH <= len(value):
            raise CommentError(f'Name is too long. Must at have less than {cls.MAX_LENGTH + 1} character')
        if re.match(cls.PATTERN, value):
            raise CommentError(f'Name must not start with a number or a space: "{value}"')
        return str.__new__(cls, value)


class CommentAttribute(StandardAttribute):
    """Long name attribute"""

    name = 'comment'

    def setter(self, obj, value: str) -> None:
        """Set the comment"""
        ln = Comment(value)  # runs check automatically during initialization
        obj.attrs.create('comment', ln.__str__())

    def getter(self, obj) -> Union[str, None]:
        """Get the comment"""
        value = self.safe_getter(obj)
        if value:
            return Comment(value)
        return None
