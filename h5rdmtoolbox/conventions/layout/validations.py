"""Module containing all validation classes"""

import abc
import typing

import h5py


class Validation(abc.ABC):
    """Validation abstract class defining the interface for all validations.
    Manages the validation. Important attribute is the `validator` (see module `validators.py`).
    The method __call__() calls the validator on the given value.
    """

    def __init__(self,
                 parent,
                 validator):
        from .dataset import Dataset
        from .group import Group
        assert isinstance(parent, (Dataset, Group))
        self.parent = parent
        self.validator = validator

    @property
    @abc.abstractmethod
    def validator(self):
        return self._validator

    @validator.setter
    @abc.abstractmethod
    def validator(self, validator):
        if validator is None:
            self._validator = None
            return
        self._validator = validator

    def visititems(self, target: h5py.Group):
        """Recursively visit all items in the target and call the method `validate`"""
        assert isinstance(target, h5py.Group)
        validators = []

        def visitor(_, obj):
            if isinstance(obj, self.obj_flt):
                validators.append(self.validator(self, obj))

        target.visititems(visitor)
        return validators

    def __call__(self, target) -> typing.Union[None,
                                               "Validator",
                                               typing.List["Validator"]]:
        """called by Layout.validate()"""
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(self, target)
        return self.validator(self, target)

    def register(self):
        """Add to layout validator container"""
        self.parent.file.validations.add(self)
