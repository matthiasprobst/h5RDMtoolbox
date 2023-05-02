"""validator module"""
import abc
import h5py
import re
import typing
import warnings


class Validator(abc.ABC):
    """Base class for all validators.

    Parameters
    ----------
    reference : str, int, float
        The reference value to compare to.
    count : int, optional
        The expected number of success for this validator. If None,
        the number of successes is not checked.
    sign : str, optional
        The sign to use for the string representation of the validator.
    """

    def __init__(self, reference: typing.Any, optional, count=None, sign: str = ' --> '):
        self.reference = reference
        self.is_optional = optional
        self.count = count
        self.sign = sign
        self.nmax = None  # number of occurrences. see GroupValidation.validate()
        self._message = f'Validator {self.__class__.__name__} has not yet been called or no message has been set!'
        self.is_called = False
        self.is_valid = None

    def __repr__(self):
        if self.count:
            return f'{self.__class__.__name__}({self.reference.__repr__()}, count={self.count})'
        return f'{self.__class__.__name__}({self.reference.__repr__()})'

    def __str__(self):
        return f'{self.__class__.__name__}({self.message})'

    def reset(self):
        """reset the validator to its initial state"""
        self._message = f'Validator {self.__class__.__name__} has not yet been called or no message has been set!'
        self.is_called = False
        self.is_valid = None

    @abc.abstractmethod
    def validate(self, value) -> bool:
        """Validate the value. To be implemented by subclasses."""

    def __call__(self, value):
        if self.is_called:
            warnings.warn(f'Validator {self.__class__.__name__} has already been called. '
                          f'Resetting now.')
            self.reset()
        self.is_valid = self.validate(value)
        self.is_called = True
        if isinstance(value, (h5py.Dataset, h5py.Group)):
            self.__set_message__(value.name, self.is_valid)
        else:
            self.__set_message__(value, self.is_valid)
        return self.is_valid

    @property
    def message(self):
        """Return a string explaining the validator"""
        return self._message

    def __set_message__(self, target: str, success: bool):
        if success:
            self._message = f'{self.__class__.__name__} succeeded for target "{target}"'
        else:
            self._message = f'{self.__class__.__name__} failed for target "{target}"'

    @message.setter
    def message(self, target_success):
        raise RuntimeError('Use __set_message__ instead')


class Regex(Validator):
    """Validator using regex"""

    def __init__(self, reference: str, optional: bool = False):
        super().__init__(reference, optional=optional, sign='=')

    def validate(self, value):
        if self.is_optional:
            return True
        return re.match(self.reference, value) is not None

    def __str__(self):
        return f're:{self.reference}'


class Equal(Validator):
    """Validator that checks if the value is equal to the reference value.
    A reference value of '*' will always return True."""

    def __init__(self, reference, optional: bool = False, count: int = None):
        super().__init__(reference=reference, optional=optional, count=count, sign='=')

    def validate(self, value):
        if self.is_optional:
            return True
        if self.reference == '*':
            return True
        return value == self.reference

    def __str__(self) -> str:
        return str(self.reference)

    def __set_message__(self, target, success):
        """Returns human-readable message of the validation result."""
        if success:
            self._message = f'{self.reference} is equal to "{target}"'
        else:
            self._message = f'{self.reference} is not equal to "{target}"'


class In(Validator):
    """Validator that checks if the value is within the reference values."""

    def __init__(self, *reference, optional: bool = False):
        super().__init__(reference, optional=optional, sign=' in ')

    def validate(self, value, *args, **kwargs):
        if self.is_optional:
            return True
        return value in self.reference

    def __set_message__(self, target: str, success: bool) -> str:
        """Returns human-readable message of the validation result."""
        if success:
            self._message = f'{self.reference} is in "{target}"'
        else:
            self._message = f'{self.reference} is not exist in "{target}"'


class GroupValidator(Validator, abc.ABC):
    """Group validator base class. Different to Validator, this class returns a list of
    found objects or None if the validator failed."""

    @abc.abstractmethod
    def validate(self, value: h5py.Group) -> typing.List[typing.Union[h5py.Group, h5py.Dataset]]:
        """validates a h5py.Group object"""

    def __call__(self, value) -> typing.Union[None, h5py.Dataset, h5py.Group]:
        if self.is_called:
            raise RuntimeError('Validator has already been called. Should not happen! Check '
                               'the code!')
        found_object = self.validate(value)
        self.is_valid = found_object is not None
        self.is_called = True
        if isinstance(value, (h5py.Dataset, h5py.Group)):
            self.__set_message__(value.name, self.is_valid)
        else:
            self.__set_message__(value, self.is_valid)
        return found_object


class ExistIn(GroupValidator):
    """Validator that checks if an HDF object is within another (to check if dataset or group exists).

    Parameters
    ----------
    reference : str
        The HDF5 object (dataset or group) to check if it exists in the given value in validate().
    """

    def __init__(self, reference: str, optional: bool = False):
        super().__init__(reference, optional=optional, sign=' exists in ')

    def validate(self,
                 value: typing.Union[h5py.Dataset, h5py.Group]) -> typing.Union[None, h5py.Dataset, h5py.Group]:
        """Check if the given value exists in the given reference.

        Parameters
        ----------
        value : typing.Union[h5py.Dataset, h5py.Group]
            The object to check.

        Returns
        -------
        Union[bool, h5py.Dataset, h5py.Group]
            If the value exists in the reference, return the value. Otherwise, return False.
        """
        if self.is_optional:
            return list(value.values())
        if not isinstance(value, (h5py.Dataset, h5py.Group)):
            raise TypeError(f'Value must be a h5py.Dataset or h5py.Group, not {type(value)}')
        if self.reference not in value:
            return None
        return value.get(self.reference)

    def __set_message__(self, target: str, success: bool) -> str:
        """Returns human-readable message of the validation result."""
        if success:
            self._message = f'"{self.reference}" exists in "{target}"'
        else:
            self._message = f'"{self.reference}" does not exist in "{target}"'


class Any(Validator):
    """An optional Validator that always returns True."""

    def __init__(self):
        super().__init__(None, optional=True, sign='=')

    def __str__(self):
        return '...'

    def __repr__(self):
        return f'{self.__class__.__name__}(opt={self.is_optional})'

    def validate(self, value, *args, **kwargs):
        return True


class ValidString(Regex):
    """Validator that checks if the value is a valid string. Rule is not to start with a space or a number."""

    def __init__(self, optional: bool = False):
        super().__init__(r'^[^ 0-9].*', optional=optional)


def guess_validator(v: typing.Any) -> Validator:
    """Guess the validator from the given value."""
    if v is Ellipsis:
        return Any()
    elif isinstance(v, (str, int, float)):
        return Equal(v)
    return v
