import inspect
import typing

import h5py

from . import validators
from .dataset import Dataset
from .group import Group
from .utils import Message
from .validations import Validation


class AttributeEqual(validators.Validator):
    """Base class for validators of attributes"""

    def __init__(self, reference):
        super().__init__(reference, False)

    def validate(self, key: str, target: typing.Union[h5py.Dataset, h5py.Group]) -> bool:
        target_attr_value = target.attrs.get(self.reference, None)
        if target_attr_value is None:
            self.failure_message = Message(f'Attribute "{self.reference}" does not exist in {target.name}')
            return False
        return True


class AnyAttribute(validators.Validator):
    """Accepts any attribute value. Per default this is NOT an optional validator"""

    def __init__(self, reference=None):
        super().__init__(reference, False)

    def validate(self, key: str, target: str) -> bool:
        """If the validator is optional, it will always will return True as it validates any attribute value.
        If it is not optional, then the key is searched in the target's attributes and if it is not found,
        the validation will fail. The value still plays no role in this validation.
        """
        if not self.is_optional:
            if key not in target.attrs:
                self.failure_message = Message(f'Attribute "{key}" does not exist in {target.name}')
                return False
        return True


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
        attrval = AttributeValidation(parent=self.parent,
                                      key=key,
                                      validator=validator)
        return attrval

    def __getitem__(self, item) -> "AttributeValidation":
        return AttributeValidation(parent=self.parent,
                                   key=item,
                                   validator=None)


class AttributeValidation(Validation):
    """Validation class for attributes"""

    def __init__(self,
                 parent: typing.Union["Dataset", "Group"],
                 key: str,
                 validator: validators.Validator):
        assert isinstance(parent, (Dataset, Group))
        self.parent = parent
        if isinstance(self.parent, Group):
            self.obj_flt = h5py.Group
        elif isinstance(self.parent, Dataset):
            self.obj_flt = h5py.Dataset
        else:
            raise TypeError('parent must be either a "GroupLayoutAttribute" or a "DatasetLayoutAttribute" but '
                            f'is {type(self.parent)}')
        self.key = key
        self.validator = validator

    def register(self):
        """Add to layout validator container"""
        self.parent.file.validations.add(self)

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

    def __repr__(self):
        return f'{self.__class__.__name__}(path="{self.parent.path}", key="{self.key}", ' \
               f'validator={self.validator.__repr__()})'

    def visititems(self, key, target) -> typing.List[validators.Validator]:
        """Recursively visit all items in the target and call the method `validate`"""
        validators = []

        def visitor(_, obj):
            if isinstance(obj, self.obj_flt):
                validators.append(self.validator(key, obj))

        target.visititems(visitor)
        return validators

    def __call__(self, target: h5py.Group) -> typing.Union[
        None, validators.Validator, typing.List[validators.Validator]]:
        """Performs the validation. This method is called by Layout.validate()"""
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(key=self.key, target=target)
        return self.validator(key=self.key, target=target)

