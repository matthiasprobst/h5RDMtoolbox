import abc
import typing

import h5py

from . import Validator
from ..utils import flatten


class ValidationResultMessage(abc.ABC):
    """Abstract class for validation result messages"""

    def __init__(self, msg):
        self.msg = msg


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

    def __getitem__(self, index: int) -> ValidationResultMessage:
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

    def print(self) -> None:
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


class GroupNotExist(ValidationResultMessage):
    """Validation result message for missing groups"""

    def __init__(self, missing_group_name: str, target_group_name: str):
        msg = f'Group {missing_group_name} does not exist in {target_group_name}'
        super().__init__(msg)
        self.missing_group_name = missing_group_name
        self.target_group_name = target_group_name

    def __repr__(self):
        return f'<GroupNotExist({self.missing_group_name}, {self.target_group_name})>'

    def __str__(self):
        return self.msg


class AttributeNotExist(ValidationResultMessage):
    """Validation result message for missing attributes"""

    def __init__(self, missing_property: str, target: typing.Union[h5py.Dataset, h5py.Group]):
        objname = type(target).__name__
        msg = f'Missing attribute "{missing_property}" of {objname} "{target.name}"'
        super().__init__(msg)


class PropertyNotExist(ValidationResultMessage):
    """Validation result message for missing properties"""

    def __init__(self, missing_property: str, target: typing.Union[h5py.Dataset, h5py.Group]):
        objname = type(target).__name__
        msg = f'Missing property "{missing_property}" of {objname} "{target.name}"'
        super().__init__(msg)
