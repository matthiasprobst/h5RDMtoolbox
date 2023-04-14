import typing

from .utils import flatten
from .validations import Validation


class ValidationResults:
    """Container for validation results"""

    def __init__(self, called_validations: typing.Union["ValidationResults", typing.List[Validation], None] = None):
        self._validations = []
        if called_validations is None:
            self._validations = []
        else:
            if isinstance(called_validations, list):
                for v in called_validations:
                    if not isinstance(v, Validation):
                        raise TypeError(f'called_validations must be a list of Validation objects,'
                                        f' not {type(v)}')
                self._validations = called_validations
            elif isinstance(called_validations, ValidationResults):
                self._validations = called_validations._validations
            else:
                raise TypeError(f'called_validations must be a list or ValidationResults object,'
                                f' not {type(called_validations)}')

    def __repr__(self):
        return f'<ValidationResults(issues: {self.total_issues()})>'

    def __getitem__(self, index: int) -> Validation:
        if not isinstance(index, int):
            raise TypeError('Index must be an integer')
        return self._validations[index]

    @staticmethod
    def concatenate_validations(results: typing.Union[Validation,
                                                      typing.List[Validation],
                                                      "ValidationResults"]) -> "ValidationResults":
        """Concatenate validation results"""
        new_validations = ValidationResults()
        if isinstance(results, ValidationResults):
            for r in results:
                if r is None:
                    continue
                new_validations._validations.extend(r._validations)
        else:
            if isinstance(results, list):
                results = flatten(results)
            else:
                results = list(results)
            for r in results:
                new_validations.add(r)
        return new_validations

    def add(self, validation: Validation) -> None:
        """Adds a validation result. Successful validations have no message. Pass None.
        If the message already exists, it is not added."""
        if not validation.validator.called:
            raise ValueError('Cannot add a validation that has not been called.')
        for v in self._validations:
            if v == validation:
                return
        self._validations.append(validation)

    def report(self) -> None:
        """Prints all validation results"""
        for r in self._validations:
            print(r.validator.message)

    def total_issues(self) -> int:
        """Returns the total number of valid validations"""
        tot = 0
        for r in self._validations:
            if not r.validator.is_optional:
                tot += not r.validator.passed
        return tot
