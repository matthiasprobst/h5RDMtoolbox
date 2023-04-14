"""Module containing all validation classes"""

import abc
import typing


class Validation(abc.ABC):
    """Validation abstract class defining the interface for all validations.
    Manages the validation. Important attribute is the `validator` (see module `validators.py`).
    The method __call__() calls the validator on the given value.
    """

    def __init__(self,
                 parent,
                 validator,
                 *args, **kwargs):
        from .dataset import Dataset
        from .group import Group
        assert isinstance(parent, (Dataset, Group))
        self.parent = parent
        self.validator = validator
        self._args = args
        self._kwargs = kwargs

    @property
    def validator(self, validator):
        self._validator = validator

    @validator.getter
    def validator(self):
        return self._validator

    @abc.abstractmethod
    def __repr__(self):
        pass

    @abc.abstractmethod
    def visititems(self, key, target) -> typing.List["Validator"]:
        pass

    def __call__(self, target) -> typing.Union[None,
                                               "Validator",
                                               typing.List["Validator"]]:
        """called by Layout.validate()"""
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(key=self.key, target=target)
        return self.validator(key=self.key, target=target)
