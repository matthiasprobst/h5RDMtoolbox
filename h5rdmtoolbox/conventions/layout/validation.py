from typing import List

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
    def __init__(self, results: List[ValidationResult]):
        self.results = results

    def print(self) -> None:
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
