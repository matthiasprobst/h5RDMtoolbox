"""Module for validators

A validator compares a value to a reference value.

The class `Validator` is the abstract class for all validators. It defines the interface for all validators.
"""

import abc
import typing

import h5py


class Validator(metaclass=abc.ABCMeta):
    """Abstract class for validators.
    A validator compares a value to a reference value and returns True if the value is valid, else False.

    Parameters
    ----------
    reference : any
        reference value
    optional : bool
        If True, the validator will not fail if the value is not present or validated
    """

    @abc.abstractmethod
    def __init__(self,
                 reference: typing.Union[int, float, str, None],
                 optional: bool):
        self.reference = reference
        self._optional = optional
        self.called = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.reference == other.reference and self.is_optional == other.is_optional

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        if self.called:
            return f'{self.__class__.__name__}({self.reference}, opt={self.is_optional}, passed={self.passed},' \
                   f' msg={self.message})'
        return f'{self.__class__.__name__}({self.reference}, opt={self.is_optional})'

    @abc.abstractmethod
    def validate(self, value: str, *args, **kwargs) -> bool:
        """main validation method, to be defined in subclasses"""

    @property
    def is_optional(self) -> bool:
        """Returns True if the validator is optional, else False"""
        return self._optional

    def __call__(self, *args, **kwargs) -> 'Validator':
        """validate

        Parameters
        ----------
        args:
            arguments to be passed to the validation method
        kwargs:
            Additional keyword arguments to be passed to the validation method
        """
        self.passed = self.validate(*args, **kwargs)
        self.called = True

    def success_message(self) -> str:
        """Returns the success message"""
        return f'{self.reference} is valid'

    def failure_message(self) -> str:
        """Returns the success message"""
        return f'{self.reference} is not valid'

    @property
    def message(self) -> str:
        """Returns the validation message"""
        if self.called:
            if self.passed:
                return self.success_message()
            return self.failure_message()
        raise RuntimeError('Validator has not been called yet')


class Equal(Validator):
    """Check if value is equal to reference."""

    def __init__(self, reference):
        super().__init__(reference, False)

    def validate(self, other):
        return self.reference == other


class Any(Validator):
    """Accepts any value. Per default this is NOT an optional validator"""

    def __init__(self, reference=None):
        super().__init__(reference, False)

    def validate(self, value: str) -> bool:
        return True


class Regex(Validator):
    """check if value matches the regular expression.
    """

    def __init__(self, reference):
        super().__init__(reference, True)

    def validate(self, value: str) -> bool:
        import re
        return re.match(self.reference, value) is not None


class HDFObjectExist(Validator):
    """Check if group exists"""

    def __init__(self, reference: typing.Union[h5py.Group, h5py.Dataset]):
        super().__init__(reference, False)

    def validate(self, target: h5py.Group):
        return self.reference in target
