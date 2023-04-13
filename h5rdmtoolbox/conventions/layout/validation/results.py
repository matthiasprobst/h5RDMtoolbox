import typing

from . import Validator
from ..utils import flatten


class ValidationResults:
    """Container for validation results"""

    def __init__(self, results: typing.Union["ValidationResults", typing.List[Validator], None] = None):
        if results is None:
            self._results = []
        else:
            if isinstance(results, list):
                self._results = results
            else:
                self._results = results._results

    def __repr__(self):
        return f'<ValidationResults(issues: {self.total_issues()})>'

    def __getitem__(self, index: int) -> Validator:
        if not isinstance(index, int):
            raise TypeError('Index must be an integer')
        return self._results[index]

    @staticmethod
    def concatenate_results(results: typing.Union[Validator,
                                                  typing.List["Validator"],
                                                  "ValidationResults"]) -> "ValidationResults":
        """Concatenate validation results"""
        new_results = ValidationResults()
        if isinstance(results, ValidationResults):
            for r in results:
                if r is None:
                    continue
                new_results._results.extend(r._results)
        else:
            if isinstance(results, list):
                results = flatten(results)
            else:
                results = list(results)
            for r in results:
                new_results.add(r)
        return new_results

    def add(self, validator: Validator) -> None:
        """Adds a validation result. Successful validations have no message. Pass None.
        If the message already exists, it is not added."""
        for r in self._results:
            if r.message == validator.message:
                return
        self._results.append(validator)

    def report(self) -> None:
        """Prints all validation results"""
        for r in self._results:
            print(r)

    def total_issues(self) -> int:
        """Returns the total number of valid validations"""
        # return sum(self.results)
        if len(self._results) == 0:
            return 0
        tot = int(not self._results[0].passed)
        for r in self._results[1:]:
            tot += not r.passed
        return tot
