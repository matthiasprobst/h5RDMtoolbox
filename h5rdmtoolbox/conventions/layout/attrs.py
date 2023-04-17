import inspect
import re
import sys
import typing
from abc import ABC

import h5py

from . import validators
from .dataset import Dataset
from .group import Group
from .utils import Message
from .validations import Validation


class AttributeValidator(validators.Validator, ABC):
    """flag class to indicate that a validator is an attribute validator"""


class Attribute:
    """Attribute interface class"""

    def __init__(self, parent, name, value=None):
        self.group = parent
        self.path = parent.path  # mimic behaviour needed by validators
        self.file = parent.file  # mimic behaviour needed by validators
        self.name = name
        self._value = None
        self.value = value

    def __repr__(self):
        if self.value is None:
            return f'Attribute(parent="{self.path.name}", name="{self.name}")'
        return f'Attribute(parent="{self.path.name}", ' \
               f'"{self.name}", value={self.value}'

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: typing.Union[str, int, float,
                                        validators.Validator,
                                        AttributeValidator,
                                        None]) -> None:
        """build the attribute validation.

        Parameters
        ----------
        value: typing.Union[str, int, float, validators.Validator, AttributeValidator, None]
            The value (validator) to validate the attribute against.
            Accepted values are:
            - None: no validation is set
            - str, int, float: the attribute value must be equal to this value, thus AttributeEqual is used
            - validators.Validator: the validator is used to validate the attribute. Must be of type AttributeValidator
            - AttributeValidator: the validator is used to validate the attribute
            - Ellipsis: the attribute must exist, thus AttributeExists is used
        """
        if value is None:
            self._value = None
            return

        if isinstance(value, validators.Validator):
            candidate_class_name = f'Attribute{value.__class__.__name__}'
            if not candidate_class_name in sys.modules[__name__].__dict__:
                raise TypeError(f'There is no attribute validation calls for {value}. Expected {candidate_class_name}')
            value = sys.modules[__name__].__dict__[candidate_class_name](reference=value.reference,
                                                                         optional=value.is_optional)

        if value is Ellipsis:
            value = AttributeExists(self.name)

        av = AttributeValidation(parent=self,
                                 validator=None)
        av.validator = value
        self._value = value


class AttributeExists(AttributeValidator):
    """Validates the existence of an attribute."""

    def __init__(self, reference=None, optional=False):
        super().__init__(reference, optional)

    def validate(self, validation, target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        """If the validator is optional, it will always will return True as it validates any attribute value.
        If it is not optional, then the key is searched in the target's attributes and if it is not found,
        the validation will fail. The value still plays no role in this validation.

        Parameters
        ----------
        validation: AttributeValidation
            The validation object
        target: typing.Union[h5py.Dataset, h5py.Group]
            The target object (Group or Dataset) to validate

        Returns
        -------
        bool
        """
        attr_name = validation.parent.name
        target_attr_value = target.attrs.get(attr_name, None)
        if target_attr_value is None:
            self.failure_message = Message(f'Attribute "{attr_name}" does not exist in {target.name}')
            return self.is_optional
        return True


class AttributeEqual(AttributeValidator):
    """Validates if an attribute is equal to a reference value."""

    def validate(self, validation, target: typing.Union[h5py.Dataset, h5py.Group]) -> typing.Union[bool, None]:
        """Validate if the reference value is equal to the attribute value. Before this can
        be checked, the existence of the attribute is checked. If the attribute does not exist but
        the attribute value is required, then will fail. If the validation is optional, then None will
        be returned"""
        # call super to check existence:
        attr_name = validation.parent.name
        attr_value = target.attrs.get(attr_name, None)
        if attr_value is None:
            if self.is_optional:
                return None
            return False

        if attr_value != self.reference:
            self.failure_message = Message(
                f'Attribute "{attr_name}" in "{target.name}" has value "{attr_value}" '
                f'but should be "{self.reference}"')
            return False
        return True


class AttributeRegex(AttributeValidator):

    def __init__(self, reference, optional=False):
        super().__init__(reference, optional)

    def validate(self, validation,
                 target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        # call super to check existence:
        attr_name = validation.parent.name
        attr_value = target.attrs.get(attr_name, None)
        if attr_value is None:
            self.failure_message = Message(f'Attribute "{attr_name}" not in "{target.name}"')
            return None

        if attr_value is None:
            return True

        re_result = re.match(self.reference, attr_value) is not None
        if not re_result:
            self.failure_message = Message(
                f'Attribute "{attr_name}" in "{target.name}" has value "{attr_value}" '
                f'but should match "{self.reference}"')
        if self.is_optional:
            return True
        return re_result


class LayoutAttributeManager:
    """Base class for layout attributes.
    Gets instantiated by the Layout classes Dataset or Group.

    Parameters
    ----------
    parent : typing.Union["Dataset", "Group"]
        The parent object. Can be a (Layout)Dataset or a (Layout)Group.
    """

    def __init__(self, parent: typing.Union["Dataset", "Group"]):
        assert isinstance(parent, (Dataset, Group))
        self.parent = parent

    def __setitem__(self, key, validator: typing.Union[float, int, str, AttributeValidator]):
        """Set an attribute validator for the given key.

        Parameters
        ----------
        key : str
            The attribute name.
        validator : float, int, str, Validator
            The validator to use for the attribute. If not a Validator, it will be wrapped in an Equal validator.

        Raises
        ------
        TypeError
            If the validator is a class, not an instance.
        """
        Attribute(parent=self.parent, name=key, value=validator)

    def __getitem__(self, item) -> "AttributeValidation":
        return Attribute(parent=self.parent, name=item)


class ConditionalLayoutAttributeManager:
    """An attribute manager that only allows setting attributes if the parent validation passed"""

    def __init__(self, validation: "Validation"):
        self.validation = validation  # the validation object to which this attribute belongs

    def __setitem__(self, key, validator):
        ConditionalAttribute(validation=self.validation, name=key, value=validator)

    def __getitem__(self, item):
        raise NotImplementedError()


class ConditionalAttribute:
    def __init__(self, validation, name, value=None):
        self.validation = validation  # the validation object to which this attribute belongs
        # this attribute is only tested for found objects in the validation
        self.name = name
        if value is not None:
            self.value = value

    @property
    def value(self):
        raise NotImplementedError()

    @value.setter
    def value(self, value) -> None:
        """build the attribute validation"""
        av = ConditionalAttributeValidation(parent=self,
                                            validation=self.validation,
                                            validator=None)
        av.validator = value


class ConditionalAttributeValidation(Validation):

    def __init__(self, parent, validation, validator):
        self.parent = parent
        self.validation = validation  # the validation object to which this attribute belongs
        self.validator = validator  # the validator to use for this attribute

    def __repr__(self):
        return f'<ConditionalAttributeValidation {self.validator}>'

    @property
    def validator(self):
        return self._validator

    @validator.setter
    def validator(self, validator: "Validator") -> None:
        if validator is None:
            self._validator = None
            return

        if isinstance(validator, (float, int, str)):
            self._validator = AttributeEqual(validator)
        elif inspect.isclass(validator):
            raise TypeError('validator must be an instance of a Validator, not a class')
        elif isinstance(validator, validators.Validator):
            self._validator = validator
        else:
            raise TypeError(f'validator must be a Validator, float, int or str, not {type(validator)}')
        # now this attribute validation object must be attached to the validation object
        # the target object must already be registered. let' make a sanity check:
        assert self.validation in self.validation.parent.file.validations
        self.validation.parent.file.add_conditional_attribute_validation(self.validation, self)


class AttributeValidation(Validation):

    def __init__(self,
                 parent,
                 validator):
        assert isinstance(parent, Attribute)
        self.parent = parent
        self.validator = validator

    def __repr__(self):
        return f'<AttributeValidation {self.validator} @"{self.parent.path}">'

    @property
    def validator(self):
        return self._validator

    @validator.setter
    def validator(self, validator: "Validator") -> None:
        if validator is None:
            self._validator = None
            return

        if isinstance(validator, (float, int, str)):
            self._validator = AttributeEqual(validator, optional=False)
        elif inspect.isclass(validator):
            raise TypeError('validator must be an instance of a Validator, not a class')
        elif isinstance(validator, validators.Validator):
            self._validator = validator
        else:
            raise TypeError(f'validator must be a Validator, float, int or str, not {type(validator)}')
        self.register()
