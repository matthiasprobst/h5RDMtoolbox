import typing

from . import validations, validators
from .path import LayoutPath
from .utils import Message


class GroupExists(validators.Validator):
    """Validator for existence of a group."""

    def validate(self, target):
        if self.is_optional:
            return True
        if self.reference not in target:
            self.failure_message = Message(f'Group "{self.reference}" does not exist in {target.name}')
            return False
        return True


class GroupValidation(validations.Validation):
    """Validation for a group"""

    def __repr__(self):
        return f'{self.__class__.__name__}(path="{self.parent.path}")'

    @property
    def validator(self):
        return self._validator

    @validator.setter
    def validator(self, validator: "Validator") -> None:
        if validator is None:
            self._validator = None
            return
        if isinstance(validator, str):
            group_name = validator
            self._validator = GroupExists(reference=group_name, optional=False)
        elif isinstance(validator, validators.Validator):
            self._validator = validator
        else:
            raise TypeError(f'validator must be a Validator, float, int or str, not {type(validator)}')
        self.register()


class Group:
    """Layout group interface"""

    def __init__(self,
                 *,
                 path: typing.Union[str, "LayoutPath"],
                 file: "Layout"):
        self.path = LayoutPath(path)
        from .layout import Layout
        assert isinstance(file, Layout)
        self.file = file

    def __repr__(self):
        return f'LayoutGroup("{self.path}")'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self.path) == str(other.path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def group(self, name: typing.Union[str, validators.Validator] = None) -> GroupValidation:
        """Initialize a group validation object

        Parameters
        ----------
        name : str, Validator
            The name of the group which results in initializing with a GroupExists validator or
            a custom validator.

        Returns
        -------
        GroupValidation
            The group validation object
        """
        if name is None:
            return self
        return GroupValidation(self, validator=name)

    def dataset(self, name=None, shape=None):
        """
        Parameters
        ----------
        name : str, Validator
            The name of the dataset
        shape : tuple, Validator
            The shape of the dataset
        """
        if name == '*' or name is None:  # the name is not checked, thus we can use Any
            name_validator = validators.Any()
        elif isinstance(name, str):  # explicit name is given, this dataset must exist!
            name_validator = validators.Equal(name)
        elif isinstance(name, validators.Validator):
            name_validator = name
        else:
            raise TypeError(f'Invalid type for name: {type(name)}')

        if shape is None:
            shape_validator = validators.Any()
        elif isinstance(shape, validators.Validator):
            shape_validator = shape
        else:
            shape_validator = validators.Equal(shape)

        dataset_validation = DatasetValidation(parent=self,
                                               name=name_validator,
                                               shape=shape_validator)
        self.file.validators.add(dataset_validation)
        return dataset_validation

    @property
    def attrs(self) -> "LayoutAttributeManager":
        """Return a new LayoutAttributeManager object for the given group name."""
        from .attrs import LayoutAttributeManager
        return LayoutAttributeManager(self)
