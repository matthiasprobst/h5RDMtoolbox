import abc
import typing

from ..._repr import okprint, failprint


class ValidationResult:
    def __init__(self, passed: bool, message: str):
        self.passed = passed
        self.message = message

    def print(self, fail: bool = True, success: bool = False) -> None:
        """Prints the validation result"""
        if self.passed and success:
            return okprint(f'Validation succeeded: {self.message}')
        if not self.passed and fail:
            failprint(f'Validation failed: {self.message}')

    def __add__(self, other):
        if isinstance(other, int):
            return self.passed + other
        return self.passed + other.passed

    def __iadd__(self, other):
        if isinstance(other, int):
            return self.passed + other
        return self.passed + other.passed


class ValidationResults:
    def __init__(self, results: typing.List[ValidationResult]):
        self.results = results

    def __getitem__(self, index: int) -> ValidationResult:
        if not isinstance(index, int):
            raise TypeError('Index must be an integer')
        return self.results[index]

    def print(self) -> None:
        """Prints all validation results"""
        for r in self.results:
            r.print()

    def total_issues(self) -> int:
        """Returns the total number of valid validations"""
        # return sum(self.results)
        if len(self.results) == 0:
            return 0
        tot = int(not self.results[0].passed)
        for r in self.results[1:]:
            tot += not r.passed
        return tot


# Validators:

class Validator(metaclass=abc.ABCMeta):
    """Abstract class for validators

    Parameters
    ----------
    reference : any
        reference value
    """

    @abc.abstractmethod
    def __init__(self,
                 reference: typing.Union[int, float, str, None],
                 optional: bool):
        self.reference = reference
        self.optional = optional

    @property
    def is_optional(self) -> bool:
        """Returns True if the validator is optional, else False"""
        return self.optional

    @abc.abstractmethod
    def __call__(self, value: typing.Any) -> bool:
        """Validates the value

        Parameters
        ----------
        value : any
            The value to validate

        Returns
        -------
        bool
            True if the value is valid, else False
        """


class Any(Validator):
    """Accepts any value"""

    def __init__(self, optional: bool = False):
        super().__init__(None, optional)

    def __call__(self, *args, **kwargs):
        return True


class Equal(Validator):
    """Check if value is equal to reference."""

    def __init__(self, reference):
        super().__init__(reference, False)

    def __call__(self, other):
        return self.reference == other


class Regex(Validator):
    """check if value matches the regular expression.
    """

    def __init__(self, reference):
        super().__init__(reference, True)

    def __repr__(self):
        return f'<Regex({self.reference})>'

    def __call__(self, value: str) -> bool:
        """check if value matches the regular expression.

        Parameters
        ----------
        value : str
            The regular expression to match against
        """
        import re
        return re.match(self.reference, value) is not None
