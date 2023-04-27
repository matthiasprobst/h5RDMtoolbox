"""Core module for the layout convention."""
import abc
import re
import typing
import warnings

import h5py


def get_subgroups(h5group: h5py.Group) -> typing.List[h5py.Group]:
    """Return a list of all groups in the given group."""
    groups = []

    def visitor(_, obj):
        """Visitor function for h5py.visititems()"""
        if isinstance(obj, h5py.Group):
            groups.append(obj)

    h5group.visititems(visitor)
    return groups


def get_h5datasets(h5group: h5py.Group) -> typing.List[h5py.Dataset]:
    """Return a list of all datasets in the given group."""
    return [h5group[k] for k in h5group.keys() if isinstance(h5group[k], h5py.Dataset)]


class ValidationResult:
    """Validation Result class."""

    def __init__(self, validation, result: bool, is_optional: bool,
                 fail_obj: typing.Union[h5py.Group, h5py.Dataset] = None):
        self.validation = validation
        self.fail_obj = fail_obj
        if result is False and is_optional is True:
            self.result = True
        else:
            self.result = result

    def __repr__(self):
        return f'ValidationResult({self.validation.__repr__()}, {self.result.__repr__()}, obj={self.fail_obj})'

    @property
    def failed(self) -> bool:
        """Return True if the validation failed."""
        return not self.result

    @property
    def succeeded(self) -> bool:
        """Return True if the validation succeeded."""
        return not self.failed


# class OptionalWrapper:
#     """Wrapper class for the Optional and Required decorators."""
#
#     def __init__(self, optional):
#         self.optional = optional
#
#     def __call__(self, obj):
#         if isinstance(obj, (int, float, str)):
#             obj = Equal(obj)
#         if not isinstance(obj, Validator):
#             raise TypeError(f'Cannot make {obj} optional')
#         obj.is_optional = self.optional
#         return obj
#
#
# Optional = OptionalWrapper(True)
# Required = OptionalWrapper(False)


# class CountWrapper:
#     """Decorator to set the maximum number of occurrences of a validation."""
#
#     def __call__(self, obj: typing.Union[int, float, str, "Validator"], n):
#         if isinstance(obj, (int, float, str)):
#             obj = Equal(obj)
#         if not isinstance(obj, Validator):
#             raise TypeError(f'Wrapper can only be used with a Validator objects')
#         obj.nmax = n
#         return obj
# Count = CountWrapper()
#
#
# class OnceWrapper:
#     """Decorator to set the maximum number of occurrences of a validation to 1."""
#
#     def __call__(self, obj: typing.Union[int, float, str, "Validator"]):
#         return Count(obj, 1)
#
#
# Once = OnceWrapper()


class Validator(abc.ABC):
    """Base class for all validators."""

    def __init__(self, reference, sign):
        self.reference = reference
        self.sign = sign
        self.nmax = None  # number of occurrences. see GroupValidation.validate()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.reference.__repr__()})'

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class Regex(Validator):
    """Validator using regex"""

    def __init__(self, reference: str):
        super().__init__(reference, sign='=')

    def __call__(self, value, *args, **kwargs):
        return re.match(self.reference, value) is not None

    def __str__(self):
        return f're:{self.reference}'


class Equal(Validator):
    """Validator that checks if the value is equal to the reference value.
    A reference value of '*' will always return True."""

    def __init__(self, reference):
        super().__init__(reference=reference, sign='=')

    def __call__(self, value, *args, **kwargs):
        if self.reference == '*':
            return True
        return value == self.reference

    def __str__(self) -> str:
        return str(self.reference)


class In(Validator):
    """Validator that checks if the value is within the reference values."""

    def __init__(self, *reference):
        super().__init__(reference, sign=' in ')

    def __call__(self, value, *args, **kwargs):
        return value in self.reference


class ExistIn(Validator):
    """Validator that checks if an HDF object is within another (to check if dataset or group exists).

    Parameters
    ----------
    reference : str
        The HDF5 object (dataset or group) to check if it exists in the given value in __call__().
    """

    def __init__(self, reference: str):
        super().__init__(reference, sign=' exists in ')

    def __call__(self,
                 value: typing.Union[h5py.Dataset, h5py.Group],
                 *args, **kwargs) -> typing.Union[bool, h5py.Dataset, h5py.Group]:
        """Check if the given value exists in the given reference.

        Parameters
        ----------
        value : typing.Union[h5py.Dataset, h5py.Group]
            The object to check.

        Returns
        -------
        Union[bool, h5py.Dataset, h5py.Group]
            If the value exists in the reference, return the value. Otherwise, return False.
        """
        if not isinstance(value, (h5py.Dataset, h5py.Group)):
            raise TypeError(f'Value must be a h5py.Dataset or h5py.Group, not {type(value)}')
        if self.reference not in value:
            return False
        return value.get(self.reference)


class Any(Validator):
    """An optional Validator that always returns True."""

    def __init__(self):
        super().__init__(None, sign='=')
        self.is_optional = True

    def __str__(self):
        return '...'

    def __repr__(self):
        return f'{self.__class__.__name__}(opt={self.is_optional})'

    def __call__(self, value, *args, **kwargs):
        return True


class ValidString(Regex):
    """Validator that checks if the value is a valid string. Rule is not to start with a space or a number."""

    def __init__(self):
        super().__init__(r'^[^ 0-9].*')


class Validation(abc.ABC):
    """Base class for all validations."""

    def __init__(self, validator: Validator):
        if validator is Ellipsis:
            validator = Any()
        elif not isinstance(validator, Validator):
            validator = Equal(validator)
        self.validator = validator
        self.is_optional = False
        self.called = False

    @abc.abstractmethod
    def validate(self, target: h5py.Group, validation_results: typing.List[ValidationResult]):
        """Validate the target object."""

    @property
    def is_required(self) -> bool:
        """Return True if this validation is required."""
        return not self.is_optional

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()})'


class AttributeValidation(Validation):
    """Validation class for attributes of a group or dataset."""

    def __init__(self, validator, parent: typing.Union["GroupValidation", "AttributeValidation"]):
        super().__init__(validator)
        self.child = None
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        parent.add(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()}, opt={self.is_optional})>'

    def __str__(self):
        if hasattr(self.parent, 'path'):
            p = self.parent.path
        else:
            p = self.parent
        if self.child is None:
            value = self.validator.__str__()
        else:
            value = self.child.validator
        return f'["{p}"].attr(name="{self.validator.__str__()}",' \
               f' value="{value}")'

    def add(self, child: Validation, overwrite=False):
        """Add successive validation to this validation object"""
        if self.child is not None and not overwrite:
            raise ValueError('child already exists and overwrite is False')
        if not isinstance(child, Validation):
            raise TypeError(f'child must be a Validation, not {type(child)}')
        self.child = child

    def validate(self, target,
                 validation_results: typing.List[ValidationResult]) -> typing.List[ValidationResult]:
        """Validate the attribute."""
        self.called = True
        if isinstance(target, (h5py.Group, h5py.Dataset)):
            attribute_names = list(target.attrs.keys())
            if len(attribute_names) == 0:
                validation_results.append(ValidationResult(self, False, self.is_optional, target))
                return validation_results

            valid_flags = []
            for k in attribute_names:
                # we need to run through all attributes before we can set the result of this validation:
                is_valid = self.validator(k)
                valid_flags.append(is_valid)
                if is_valid:
                    # validation succeeded:
                    if self.child is not None:
                        validation_results = self.child.validate(target.attrs[k], validation_results)
            # now we ran through all attributes and can set the result of this validation:
            validation_results.append(ValidationResult(self, any(valid_flags), self.is_optional, target))

        else:
            # validate the value of an attribute
            is_valid = self.validator(target)
            validation_results.append(ValidationResult(self, is_valid, self.is_optional, target))
        return validation_results

    def dumps(self, indent: int):
        """Prints the validation specification to a string"""
        print(' ' * indent + repr(self))
        if self.child:
            self.child.dumps(indent + 2)


class PropertyValidation(Validation):
    """Property Validation class"""

    def __init__(self, name, validator, parent):
        super().__init__(validator)
        self.name = name
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        parent.add(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()})>'

    def __str__(self):
        return f'["{self.parent.parent.path}"].dataset({self.name}{self.validator.sign}{self.validator.__str__()})'

    def validate(self, target: h5py.Dataset,
                 validation_results: typing.List[ValidationResult]) -> typing.List[ValidationResult]:
        """Validate the dataset property"""
        self.called = True
        if not isinstance(target, h5py.Dataset):
            raise TypeError(f'PropertyValidation can only be applied to datasets, not {type(target)}')

        prop = target.__getattribute__(self.name)
        is_valid = self.validator(prop)
        validation_results.append(ValidationResult(self, is_valid, self.is_optional))
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
        av = AttributeValidation(name_validator, self.parent)
        if value_validator is Ellipsis:
            value_validator = Any()
        elif isinstance(value_validator, (str, int, float)):
            value_validator = Equal(value_validator)
        AttributeValidation(value_validator, av)

    def __setitem__(self, name_validator, value_validator):
        self.add(name_validator, value_validator)

    def __getitem__(self, name_validator):
        AttributeValidation(name_validator, self.parent)


class _BaseGroupAndDatasetValidation(Validation, abc.ABC):
    """Base class for group and dataset validation

    Parameters
    ----------
    validator : Validator
        The validator to be applied to the group name
    parent : GroupValidation
        The parent validation object
    """

    def __init__(self,
                 validator: Validator,
                 parent: Validation):
        super().__init__(validator)
        self.parent = parent
        self.children = []
        try:
            self.is_optional = validator.is_optional
        except AttributeError:
            pass

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator.__repr__()}, opt={self.is_optional})>'

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

    def add_child(self, child: Validation) -> Validation:
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

        for registrated_child in self.children:
            if registrated_child.parent == child.parent and \
                    registrated_child.validator.reference == child.validator.reference and \
                    isinstance(registrated_child, type(child)):
                return registrated_child
        self.children.append(child)
        return child

    add = add_child  # alias

    def dumps(self, indent: int):
        """Prints the validation specification to a string"""
        print(' ' * indent + repr(self))
        for child in self.children:
            child.dumps(indent=indent + 2)

    @abc.abstractmethod
    def validate(self, target: h5py.Group, validation_results: typing.List[ValidationResult]):
        pass


class DatasetValidation(_BaseGroupAndDatasetValidation):
    """Dataset validation"""

    def __str__(self):
        prop_children = [child for child in self.children if isinstance(child, PropertyValidation)]
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
            is_valid = self.validator(dataset.name.rsplit('/', 1)[-1])
            valid_flags.append(is_valid)
            if is_valid:
                for child in self.children:
                    validation_results = child.validate(dataset, validation_results)
        validation_results.append(ValidationResult(self, any(valid_flags), self.is_optional))
        return validation_results


class GroupValidation(_BaseGroupAndDatasetValidation):
    """Group validation
    """

    def validate(self, target, validation_results) -> typing.List[ValidationResult]:
        """Validate the group"""
        self.called = True
        if isinstance(self.validator, (Equal, ExistIn)):
            if self.validator.reference == '*':
                groups = get_subgroups(target)
                groups.append(target)
                for group in groups:
                    for child in self.children:
                        validation_results = child.validate(group, validation_results)
                return validation_results

        identified_obj = self.validator(target)
        if isinstance(identified_obj, (h5py.Group, h5py.Dataset)):
            target = identified_obj
        is_valid = identified_obj is not False
        validation_results.append(ValidationResult(self, is_valid, self.is_optional, target))
        if is_valid:
            # validation succeeded:
            for child in self.children:
                validation_results = child.validate(target, validation_results)

        return validation_results

    def define_dataset(self,
                       name: typing.Union[str, Validator, None] = None,
                       opt: bool = None,
                       **properties) -> DatasetValidation:
        """Add a dataset specification

        Parameters
        ----------
        name : str, Validator, optional=None
            The name of the dataset, by default None
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

        dv = self.add(dv)
        for name, value in properties.items():
            _ = PropertyValidation(name, value, dv)

        # overwrite whatever the name validator says, if the user specified opt
        if opt is not None:
            dv.is_optional = opt
        return dv

    def define_group(self, name: typing.Union[str, Validator, None] = None) -> "GroupValidation":
        """Add a group validation object"""
        if isinstance(name, str):
            name = ExistIn(name)
        elif name is None:
            name = Any()
        gv = GroupValidation(name, self)
        return self.add(gv)

    def exists(self, n):
        """Refines the number of occ"""


class Layout(GroupValidation):
    """Layout validation main interface class to user"""

    def __init__(self):
        super().__init__(Equal(None), None)
        self._validation_results = []

    def __repr__(self):
        if self.total:
            return f'Layout(passed={self.success_ratio * 100:.1f}%)'
        return f'Layout()'

    def define_group(self, name: typing.Union[str, Validator, None] = None) -> GroupValidation:
        """Add a group validation object"""
        if isinstance(name, str):
            name = ExistIn(name)
        elif name is None:
            name = Any()
        gv = GroupValidation(name, self)
        return self.add(gv)

    def __getitem__(self, item: typing.Union[str, Validator]) -> Validation:
        # TODO if not yet registered, register it, otherwise return existing
        if item == '/':
            return self
        return self.define_group(item)

    def validate(self, target: h5py.Group) -> typing.List[ValidationResult]:
        """Validate the file using this layout specification"""
        if not isinstance(target, h5py.Group):
            with h5py.File(target) as f:
                return self.validate(f)

        assert target.name == '/'
        self._validation_results = []
        for child in self.children:
            if isinstance(child, AttributeValidation):
                self._validation_results = child.validate(target, self._validation_results)
            elif isinstance(child, GroupValidation):
                self._validation_results = child.validate(target, self._validation_results)
            elif isinstance(child, DatasetValidation):
                self._validation_results = child.validate(target, self._validation_results)
            else:
                raise TypeError(f'Unknown child type: {type(child)}')

        assert len(self.specified_validations) == len(self.called_validations) + len(self.inactive_validations)
        return self.validation_results

    @property
    def validation_results(self) -> typing.List[ValidationResult]:
        """List of validation results"""
        return [r for r in self._validation_results if r.validation.is_required]

    @property
    def success_ratio(self):
        """Success ratio"""
        if self.total == 0:
            if not self.specified_validations:
                warnings.warn('No specifications registered to this layout, thus success '
                              'ratio will always be 1.0', UserWarning)
                return 1.0
            raise ValueError('No validations performed yet')
        return (self.total - self.fails) / self.total

    def report(self):
        """Print a report of the validation results"""
        print('Layout Validation report')
        print('------------------------')
        print(f'Number of validations (called/specified): {len(self.called_validations)}/'
              f'{len(self.specified_validations)}')
        print(f'Number of inactive validations: {len(self.inactive_validations)}')
        print(f'Success rate: {self.success_ratio * 100:.1f}% (n_fails={self.fails})')

    @property
    def is_validated(self) -> bool:
        """True if the validation has been performed"""
        return self.fails == 0

    @property
    def fails(self) -> int:
        """Number of failed validations"""
        return sum(int(r.failed) for r in self.validation_results)

    @property
    def total(self) -> int:
        """Total number of performed validations"""
        return len(self.validation_results)

    @property
    def specified_validations(self) -> typing.List[Validation]:
        """Number of specified validations"""

        def _count(children: typing.List, validations):
            if children is None:
                return validations
            if not isinstance(children, (list, tuple)):
                children = [children, ]
            for child in children:
                validations.append(child)
                if hasattr(child, 'children'):
                    validations = _count(child.children, validations)
                if hasattr(child, 'child'):
                    validations = _count(child.child, validations)
            return validations

        return _count(self.children, [])

    @property
    def called_validations(self) -> typing.List[Validation]:
        """Return the list of called validations"""

        def _count(children: typing.List, _called_validations):
            if children is None:
                return _called_validations
            if not isinstance(children, (list, tuple)):
                children = [children, ]
            for child in children:
                if child.called:
                    _called_validations.append(child)
                if hasattr(child, 'children'):
                    _called_validations = _count(child.children, _called_validations)
                if hasattr(child, 'child'):
                    _called_validations = _count(child.child, _called_validations)
            return _called_validations

        return _count(self.children, [])

    @property
    def inactive_validations(self) -> typing.List[Validation]:
        """Return the list of inactive validations"""

        def _count(children: typing.List, _called_validations):
            if children is None:
                return _called_validations
            if not isinstance(children, (list, tuple)):
                children = [children, ]
            for child in children:
                if not child.called:
                    _called_validations.append(child)
                if hasattr(child, 'children'):
                    _called_validations = _count(child.children, _called_validations)
                if hasattr(child, 'child'):
                    _called_validations = _count(child.child, _called_validations)
            return _called_validations

        return _count(self.children, [])

    def get_failed_validations(self) -> typing.List[ValidationResult]:
        """Get failed validations"""
        return [r for r in self.validation_results if r.failed]

    def get_succeeded_validations(self) -> typing.List[ValidationResult]:
        """Get succeeded validations"""
        return [r for r in self.validation_results if r.succeeded]

    def print_failed_validations(self, n: int = None):
        """Print (calls __str__()) all failed validations
        Parameters
        ----------
        n: int
            Number of failed validations to print. Default prints all
        """
        failed_validations = self.get_failed_validations()
        if n is None:
            n = len(failed_validations)
        for r in failed_validations[0:n]:
            print(r.validation)

    def dumps(self, indent: int = 0):
        """Prints the validation specification to the console"""
        for child in self.children:
            child.dumps(indent)
