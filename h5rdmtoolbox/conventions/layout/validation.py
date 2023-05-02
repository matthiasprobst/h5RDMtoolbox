import abc
import copy
import h5py
import typing

from .utils import get_h5datasets, get_subgroups
from .validators import Validator, Equal, Any, guess_validator, ExistIn


class ValidationResult:
    """Validation Result class.

    Parameters
    ----------
    validation : Validation
        The validation object that was called.
    result : bool
        The result of the validation.
    fail_obj : h5py.Group or h5py.Dataset
        The object that failed the validation.
    """

    def __init__(self, validation, result, message):
        self.validation = validation
        self.result = result
        self.message = message

    def __str__(self) -> str:
        """Return human-readable string representation of the validation result."""
        return self.message

    def __repr__(self):
        # txt = f'ValidationResult({self.validation.__repr__()}'
        if self.result:
            from ..._repr import oktext
            return f'ValidationResult({oktext(self.message)})'
        from ..._repr import failtext
        return f'ValidationResult({failtext(self.message)})'

        # return f'ValidationResult({self.validation.__repr__()},' \
        #        f' res={self.result.__repr__()},' \
        #        f' obj={self.obj_name})'

    @property
    def failed(self) -> bool:
        """Return True if the validation failed."""
        return not self.result

    @property
    def succeeded(self) -> bool:
        """Return True if the validation succeeded."""
        return self.result


class Validation(abc.ABC):
    """Base class for all validations."""

    def __init__(self):
        self.called = False

    @abc.abstractmethod
    def reset(self):
        """Reset all validators. Set them to un-called status"""

    @abc.abstractmethod
    def validate(self, target: h5py.Group, validation_results: typing.List[ValidationResult]):
        """Validate the target object."""

    # @abc.abstractmethod
    def get_explanation(self, target: str, success: bool) -> str:
        """Return a string explaining the validation"""
        if success:
            return f'{self.__class__.__name__} succeeded for target "{target}"'
        return f'{self.__class__.__name__} failed for target "{target}"'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()})'


class AttributeValidation(Validation):
    """Validation class for attributes of a group or dataset.

    Parameters
    ----------
    validators : List[Tuple[Validator, Validator]]
        List of tuples containing the name and value validators.
    parent : Union[GroupValidation, AttributeValidation]
        The parent validation, e.g. dataset or group validation
    """

    def __init__(self,
                 validators: typing.List[typing.Tuple[Validator, Validator]],  # list of name-value-validators
                 # this solves the standard_name once and specific units to it problem.
                 parent: typing.Union["GroupValidation", "AttributeValidation"],
                 count: int = None):
        super().__init__()
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        self.validators = validators
        self.count = count
        parent.add_subsequent_validation(self)  # add this attribute to a parent (group or dataset) validation

    def __repr__(self) -> str:
        out = f'{self.__class__.__name__}('
        valstr = [f'{validator[0].__repr__()}={validator[1].__repr__()}' for validator in
                  self.validators]
        out += ', '.join(valstr)
        out += f' in {self.parent.__repr__()})'
        return out

    def __str__(self):
        if hasattr(self.parent, 'path'):
            p = f'{self.parent.path}{self.parent.validator.__str__()}'
        else:
            p = self.parent
        valstr = [f'{validator[0].__repr__()}={validator[1].__repr__()}' for validator in
                  self.validators]
        return f'["{p}"].attr({valstr})'

    def reset(self):
        """Reset all validators. Set them to un-called status"""
        for v in self.validators:
            v[0].reset()
            v[1].reset()

    def add(self, child: Validation, overwrite=False):
        """Add successive validation to this validation object"""
        if self.child is not None and not overwrite:
            raise ValueError('child already exists and overwrite is False')
        if not isinstance(child, Validation):
            raise TypeError(f'child must be a Validation, not {type(child)}')
        self.child = child

    def validate(self, target,
                 validation_results: typing.List[ValidationResult]) -> typing.List[ValidationResult]:
        """Validate the attribute(s).

        ..note::

            An AttributeValidation can have one or more validators. If any of these fails, the full validation fails.
            Exception is if one of the failed validators is optional.

        Parameters
        ----------
        target : Union[h5py.Group, h5py.Dataset]
            The target object to validate.
        validation_results : List[ValidationResult]
            The list of validation results to append to.

        Returns
        -------
        List[ValidationResult]
            The list of validation results.
        """
        self.called = True
        if not isinstance(target, (h5py.Group, h5py.Dataset)):
            raise TypeError(f'target must be a h5py.Group or h5py.Dataset, not {type(target)}')
        attribute_dict = dict(target.attrs.items())
        if len(attribute_dict) == 0:
            _m = []
            for  v in self.validators:
                _m.append(f'{v[0].__repr__()}={v[1].__repr__()}')
            validation_results.append(ValidationResult(self,
                                                       False,
                                                       message=f'no attributes in "{target.name}". '
                                                               'Could not apply the following '
                                                               f'validator(s): {_m}'))
            return validation_results

        validation_flags = []  # assume that the validation will succeed
        for name_validator, value_validator in self.validators:
            # we need to run through all attributes before we can set the result of this validation:
            for ak, av in attribute_dict.items():
                # validate the name:
                name_is_validated = copy.deepcopy(name_validator)(ak)
                if name_is_validated:
                    # validate the value:
                    value_is_validated = copy.deepcopy(value_validator)(av)
                    if value_is_validated:
                        validation_flags.append(1)
                        break

        # all attributes must have been passed:
        is_valid = len(self.validators) == sum(validation_flags)
        if is_valid:
            message = f'"{target.name}" has all required attributes: ' \
                      f'[{", ".join([v[0].__repr__() for v in self.validators])}]'
        else:
            message = f'"{target.name}" is missing required attributes: ' \
                      f'[{", ".join([v[0].__repr__() for v in self.validators])}]'
        validation_results.append(
            ValidationResult(self, is_valid, message=message)
        )
        return validation_results

    def dumps(self, indent: int):
        """Prints the validation specification to a string"""
        print(' ' * indent + repr(self))

    def get_explanation(self, target: str, success: bool) -> str:
        """Return a string explaining the validation"""
        if success:
            return f'{self.__class__.__name__} succeeded for target "{target}"'
        return f'{self.__class__.__name__} failed for target "{target}"'


class PropertyValidation(Validation):
    """Property Validation class"""

    def __init__(self, name, validator, parent):
        super().__init__()
        self.validator = guess_validator(validator)
        self.name = name
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        parent.add_subsequent_validation(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()})>'

    def __str__(self):
        return f'["{self.parent.path}{self.parent.validator.__str__()}"].dataset({self.name}{self.validator.sign}{self.validator.__str__()})'

    def reset(self):
        self.validator.reset()

    def validate(self, target: h5py.Dataset,
                 validation_results: typing.List[ValidationResult]) -> typing.List[ValidationResult]:
        """Validate the dataset property"""
        self.called = True
        if not isinstance(target, h5py.Dataset):
            raise TypeError(f'PropertyValidation can only be applied to datasets, not {type(target)}')

        prop = target.__getattribute__(self.name)
        is_valid = self.validator(prop)
        validation_results.append(ValidationResult(self, is_valid, message=self.validator.message))
        return validation_results

    def dumps(self, indent: int):
        """Prints the validation specification to a string"""
        print(' ' * indent + repr(self))


class AttributeValidationManager:
    """Attribute validation manager for a group or dataset validation

    Parameters
    ----------
    parent : Validation
        The parent validation object (group or dataset)
    """

    def __init__(self, parent: "Validation"):
        self.parent = parent

    def add(self,
            name_validator: typing.Union[str, Validator],
            value_validator: typing.Union[int, float, str, Validator]):
        """Add the name and value attribute validators"""
        name_validator = guess_validator(name_validator)
        value_validator = guess_validator(value_validator)
        AttributeValidation(validators=[(name_validator, value_validator), ], parent=self.parent)

    def __setitem__(self, name_validator, value_validator):
        self.add(name_validator, value_validator)

    def __getitem__(self, name_validator):
        return AttributeValidation(name_validator, self.parent)


class BaseGroupAndDatasetValidation(Validation, abc.ABC):
    """Base class for group and dataset validation

    Parameters
    ----------
    validator : Validator
        The validator to be applied to the group name
    parent : GroupValidation or None
        The parent validation object. If there is no parent, parent is None.
    """

    def __init__(self,
                 validator: Validator,
                 parent: typing.Union[Validation, None]):
        super().__init__()
        if validator is Ellipsis:
            validator = Any()
        elif not isinstance(validator, Validator):
            validator = Equal(validator)
        self.validator = validator
        self.parent = parent
        self.subsequent_validations = []

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()})>'

    def reset(self):
        """Reset the validator"""
        self.validator.reset()

    @abc.abstractmethod
    def validate(self, target: h5py.Group, validation_results: typing.List[ValidationResult]):
        """Call the validation"""
        pass

    @property
    def path(self) -> str:
        """Return the path of the parent group or dataset"""
        if self.parent is None:
            return '/'
        return '' + self.parent.path

    @property
    def attrs(self) -> AttributeValidationManager:
        """Attribute validation manager for this group or dataset"""
        return AttributeValidationManager(self)

    @attrs.setter
    def attrs(self, attrs: typing.Dict):
        """Set multiple attribute validators at once. See also specify_attrs()

        Parameters
        ----------
        attrs : typing.Dict
            The attribute validators to be set
        """
        if not isinstance(attrs, dict):
            raise TypeError(f'attrs must be a dict, not {type(attrs)}')
        return self.specify_attrs(attrs)

    def specify_attrs(self, attrs: typing.Dict, count: typing.Union[int, None] = None) -> AttributeValidation:
        """Add one or multiple attribute validators"""
        validators = [(guess_validator(vn), guess_validator(vv)) for vn, vv in attrs.items()]
        return AttributeValidation(validators=validators, parent=self, count=count)

    def add_subsequent_validation(self, child: Validation) -> Validation:
        """Add a child validation object to be called after this validation succeeded

        Parameters
        ----------
        child : Validation
            The child validation object to be called after this validation succeeded

        Returns
        -------
        Validation
            The child validation object.

        """
        if not isinstance(child, Validation):
            raise TypeError(f'child must be a Validation, not {type(child)}')

        for registrated_child in self.subsequent_validations:
            if registrated_child.parent == child.parent:
                if type(registrated_child) == type(child):
                    if isinstance(child, AttributeValidation):
                        if len(child.validators) == len(registrated_child.validators):
                            if all([child.validators[i][0].reference == registrated_child.validators[i][0].reference
                                    and child.validators[i][1].reference == registrated_child.validators[i][1].reference
                                    for i in range(len(child.validators))]):
                                return registrated_child
                    else:
                        if registrated_child.validator.reference == child.validator.reference:
                            return registrated_child
        self.subsequent_validations.append(child)
        return child

    def dumps(self, indent: int):
        """Prints the validation specification to a string"""
        print(' ' * indent + repr(self))
        for child in self.subsequent_validations:
            child.dumps(indent=indent + 2)


class DatasetValidation(BaseGroupAndDatasetValidation):
    """Dataset validation"""

    def __str__(self):
        prop_children = [child for child in self.subsequent_validations if isinstance(child, PropertyValidation)]
        if len(prop_children) == 0:
            return f'["{self.parent.path}"].dataset(name="{self.validator.__str__()}")'
        return '\n'.join(
            f'["{self.parent.path}"].dataset(name="{self.validator.__str__()}",'
            f' {child.name}={child.validator.__str__()})'
            for child in prop_children)

    def validate(self, h5group: h5py.Group,
                 validation_results: typing.List[ValidationResult]) -> typing.List[ValidationResult]:
        """Validate datasets of a group"""
        self.called = True
        valid_flags = []
        for dataset in get_h5datasets(h5group):
            is_valid = copy.deepcopy(self.validator)(dataset.name.rsplit('/', 1)[-1])
            valid_flags.append(is_valid)
            if is_valid:
                for child in self.subsequent_validations:
                    validation_results = child.validate(dataset, validation_results)

        if len(valid_flags) == 0:
            dataset_validation_flag = self.validator.is_optional
        else:
            dataset_validation_flag = all(valid_flags)

        if dataset_validation_flag:
            message = f'ds validation "{self.validator}" succeeded for {h5group.name}'
        else:
            message = f'ds validation "{self.validator}" failed for {h5group.name}'
        validation_results.append(ValidationResult(self, dataset_validation_flag, message=message))
        return validation_results


class GroupValidation(BaseGroupAndDatasetValidation):
    """Group validation
    """

    def explain(self, group_name, result) -> str:
        """Return a human-readable explanation of the validation result"""
        return self.validator.get_explanation(group_name, result)

    def validate(self, target, validation_results) -> typing.List[ValidationResult]:
        """Validate the group"""
        self.called = True
        if isinstance(self.validator, (Equal, ExistIn)):
            if self.validator.reference == '*':
                groups = get_subgroups(target)
                groups.append(target)
                for group in groups:
                    for child in self.subsequent_validations:
                        validation_results = child.validate(group, validation_results)
                return validation_results

        if self.validator.is_called:
            self.validator.reset()
        found_object = self.validator(target)
        if isinstance(found_object, bool):
            found_object = target

        validation_results.append(ValidationResult(self,
                                                   self.validator.is_valid,
                                                   message=self.validator.message))
        if self.validator.is_valid:
            # validation succeeded:
            for child in self.subsequent_validations:
                validation_results = child.validate(found_object, validation_results)

        return validation_results

    def specify_dataset(self,
                        name: typing.Union[str, Validator, None] = None,
                        opt: bool = None,
                        **properties) -> DatasetValidation:
        """Add a dataset specification

        Parameters
        ----------
        name : str, Validator, optional=None
            The name of the dataset, by default None
        opt : bool, optional=None
            Whether the validation is optional, by default None
        **properties
            The dictionary containing the properties of an HDF5 dataset and their validators

        Returns
        -------
        DatasetValidation
            The dataset validation object
        """
        if name is None:
            name = Any()
        dv = DatasetValidation(name, self)

        dv = self.add_subsequent_validation(dv)
        for name, value in properties.items():
            _ = PropertyValidation(name, value, dv)

        # overwrite whatever the name validator says, if the user specified opt
        if opt is not None:
            dv.is_optional = opt
        return dv

    def specify_group(self, name: typing.Union[str, Validator, None] = None) -> "GroupValidation":
        """Add a group validation object"""
        if isinstance(name, str):
            name = ExistIn(name)
        elif name is None:
            name = Any()
        gv = GroupValidation(name, self)
        return self.add_subsequent_validation(gv)
