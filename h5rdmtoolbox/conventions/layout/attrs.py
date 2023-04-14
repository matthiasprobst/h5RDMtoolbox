import inspect
import typing

import h5py

from . import validators
from .dataset import Dataset
from .group import Group
from .utils import Message
from .validations import Validation


class Attribute:

    def __init__(self, parent, name, value=None):
        self.group = parent
        self.path = parent.path  # mimic behaviour needed by validators
        self.file = parent.file  # mimic behaviour needed by validators
        self.name = name
        if value is not None:
            self.value = value

    @property
    def value(self):
        raise NotImplementedError()

    @value.setter
    def value(self, value) -> None:
        """build the attribute validation"""
        av = AttributeValidation(parent=self,
                                 validator=None)
        av.validator = value


class AttributeEqual(validators.Validator):
    """Base class for validators of attributes"""

    def __init__(self, reference):
        super().__init__(reference, False)

    def validate(self, validation, target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        attr = validation.parent
        target_attr_value = target.attrs.get(attr.name, None)
        if target_attr_value is None:
            self.failure_message = Message(f'Attribute "{attr.name}" does not exist in {target.name}')
            if self.is_optional:
                True
            return False
        if target_attr_value != self.reference:
            self.failure_message = Message(
                f'Attribute "{attr.name}" in "{target.name}" has value "{target_attr_value}" '
                f'but should be "{self.reference}"')
            return False
        return True


Equal = AttributeEqual


class AnyAttribute(validators.Validator):
    """Accepts any attribute value. Per default this is NOT an optional validator"""

    def __init__(self, reference=None):
        super().__init__(reference, False)

    def validate(self, validation, target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        """If the validator is optional, it will always will return True as it validates any attribute value.
        If it is not optional, then the key is searched in the target's attributes and if it is not found,
        the validation will fail. The value still plays no role in this validation.
        """
        attr = validation.parent
        target_attr_value = target.attrs.get(attr.name, None)
        if target_attr_value is None:
            self.failure_message = Message(f'Attribute "{attr.name}" does not exist in {target.name}')
            return self.is_optional
        return True


Any = AnyAttribute


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

    def __setitem__(self, key, validator: typing.Union[float, int, str, validators.Validator]):
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
        # attrval = AttributeValidation(parent=self.parent,
        #                               key=key,
        #                               validator=validator)
        Attribute(parent=self.parent, name=key, value=validator)

    def __getitem__(self, item) -> "AttributeValidation":
        return Attribute(parent=self.parent, name=item)
        # return AttributeValidation(parent=self.parent,
        #                            key=item,
        #                            validator=None)


class AttributeValidation(Validation):
    def __init__(self,
                 parent,
                 validator):
        assert isinstance(parent, Attribute)
        self.parent = parent
        self.validator = validator

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
        self.register()

    # def get_hdf5_filter(self):
    #     if isinstance(self.parent.group, Group):
    #         return h5py.Group
    #     return h5py.Dataset
