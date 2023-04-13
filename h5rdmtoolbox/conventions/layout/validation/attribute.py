import abc
import copy
import typing

import h5py

from . import Validator, Message


class AttributeValidator(Validator):
    """Abstract class for validators that validate attributes"""

    @abc.abstractmethod
    def validate(self, key: str,
                 target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        pass

    def __call__(self,
                 key: str,
                 target: typing.Union[h5py.Dataset, h5py.Group]) -> "Validator":
        """validate

        Parameters
        ----------
        key: str
            The attribute key to validate
        target : typing.Union[h5py.Dataset, h5py.Group]
            The target group or dataset where to validate the attribute
        """
        self.passed = self.validate(key, target)
        self.called = True
        return copy.deepcopy(self)


class AttributeEqual(AttributeValidator):
    """Base class for validators of attributes"""

    def __init__(self, reference):
        super().__init__(reference, False)

    def validate(self, key: str, target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        target_attr_value = target.attrs.get(self.reference, None)
        if target_attr_value is None:
            self.failure_message = Message(f'Attribute "{self.reference}" does not exist in {target.name}')
            return False
        return True


class AnyAttribute(AttributeValidator):
    """Accepts any attribute value. Per default this is NOT an optional validator"""

    def __init__(self, reference=None):
        super().__init__(reference, False)

    def validate(self, key: str, target: str) -> bool:
        """If the validator is optional, it will always will return True as it validates any attribute value.
        If it is not optional, then the key is searched in the target's attributes and if it is not found,
        the validation will fail. The value still plays no role in this validation.
        """
        if not self.is_optional:
            if key not in target.attrs:
                self.failure_message = Message(f'Attribute "{key}" does not exist in {target.name}')
                return False
        return True
