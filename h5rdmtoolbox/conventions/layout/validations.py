"""Module containing all validation classes"""

import abc
import copy
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
        self.conditional_validators = []  # to be called if self.validator succeeded

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

    @property
    def passed(self):
        return self.validator.passed

    @property
    def called(self):
        return self.validator.called

    @property
    def is_optional(self):
        return self.validator.is_optional

    @property
    def is_required(self):
        return not self.validator.is_optional

    @property
    def message(self):
        return self.validator.message

    def perform_conditional_validation(self, source_validation, target):
        validators = []
        if source_validation in self.parent.file.conditional_attribute_validations:
            assert source_validation.validator.passed
            # we found a candidate, more specifically a group: target. and there are conditional validators. let's run them:
            for conditional_validator in self.parent.file.conditional_attribute_validations[source_validation]:
                from .attrs import AttributeValidation
                # easiest is to just create a new validator based on the passed one
                attr_name = conditional_validator.parent.name
                tmp_validator = AttributeValidation(parent=self.parent.attrs[attr_name],
                                                    validator=conditional_validator.validator)

                validators.append(tmp_validator.validator(tmp_validator, target))
        return validators

    def visititems(self, target: h5py.Group):
        """Recursively visit all items in the target and call the method `validate`"""
        assert isinstance(target, h5py.Group)

        new_validation_instance = copy.deepcopy(self)

        validators: typing.List[Validation] = [new_validation_instance.validator(new_validation_instance, target), ]
        assert validators[0].validator.called

        if validators[0].validator.passed:
            for condvalidator in self.perform_conditional_validation(validators[0], target):
                validators.append(condvalidator)

        def visitor(_, obj):
            if isinstance(obj, self.get_hdf5_filter()):
                # we need make a copy otherwise list of validators will be identical
                new_validation_instance = copy.deepcopy(self)
                validators.append(new_validation_instance.validator(new_validation_instance, obj))

                if validators[-1].validator.passed:
                    for condvalidator in self.perform_conditional_validation(self, obj):
                        validators.append(condvalidator)

        target.visititems(visitor)

        assert all([validators[0] != v for v in validators[1:]])  # check that all validators are different
        return validators

    def __call__(self, target) -> typing.Union[None,
                                               "Validator",
                                               typing.List["Validator"]]:
        """called by Layout.validate()"""
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(target)
        return self.validator(self, target)

    def register(self):
        """Add to layout validator container"""
        self.parent.file.validations.add(self)

    def get_hdf5_filter(self):
        return h5py.Dataset, h5py.Group
