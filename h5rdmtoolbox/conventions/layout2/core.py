import abc
import copy
import typing

import h5py


def get_h5groups(h5group: h5py.Group) -> typing.List[h5py.Group]:
    return [h5group[k] for k in h5group.keys() if isinstance(h5group[k], h5py.Group)]


def get_h5datasets(h5group: h5py.Group) -> typing.List[h5py.Dataset]:
    return [h5group[k] for k in h5group.keys() if isinstance(h5group[k], h5py.Dataset)]


class OptReqWrapper:

    def __init__(self, optional):
        self.optional = optional

    def __call__(self, obj):
        if isinstance(obj, (int, float, str)):
            obj = Equal(obj)
        if not isinstance(obj, Validator):
            raise TypeError(f'Cannot make {obj} optional')
        obj.is_optional = self.optional
        return obj


Optional = OptReqWrapper(True)
Required = OptReqWrapper(False)


class Validator:

    def __init__(self, reference):
        self.reference = reference

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.reference}")'

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        pass


class Regex(Validator):

    def __call__(self, value):
        import re
        return re.match(self.reference, value) is not None


class Equal(Validator):

    def __call__(self, value):
        return value == self.reference


class In(Validator):

    def __init__(self, *reference):
        super().__init__(reference)

    def __call__(self, value):
        return value in self.reference


class Any(Validator):
    def __init__(self):
        super().__init__(None)

    def __call__(self, value):
        return True


class Validation:

    def __init__(self, validator: Validator):
        if validator is Ellipsis:
            validator = Any()
        elif not isinstance(validator, Validator):
            validator = Equal(validator)
        self.validator = validator
        self.is_optional = False
        self.succeeded = False
        self.called = False

    def validate(self, target: h5py.Group):
        pass

    @property
    @abc.abstractmethod
    def fails(self):
        pass

    @property
    def is_required(self):
        return not self.is_optional

    @property
    def is_valid(self):
        return self.called and self.succeeded

    @property
    def is_invalid(self):
        return self.called and not self.succeeded

    @property
    def is_unchecked(self):
        return not self.called

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator})'


class AttributeValidation(Validation):

    def __init__(self, validator, parent: "GroupValidation"):
        super().__init__(validator)
        self.child = None
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        parent.add(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator})>'

    @property
    def fails(self):
        n = 0
        if self.is_invalid:
            n = 1
        child = copy.deepcopy(self.child)
        if child is not None:
            n += child.fails
        return n

    def add(self, child: Validation, overwrite=False):
        if self.child is not None and not overwrite:
            raise ValueError('child already exists and overwrite is False')
        if not isinstance(child, Validation):
            raise TypeError(f'child must be a Validation, not {type(child)}')
        self.child = child

    def validate(self, target):
        self.called = True
        validations = []
        if isinstance(target, (h5py.Group, h5py.Dataset)):
            for k in target.attrs.keys():
                if self.validator(k):
                    validations.append(k)
                    # validation succeeded:
                    if self.child is not None:
                        self.child.validate(target.attrs[k])
        else:
            # validate the value of an attribute
            if self.validator(target):
                validations.append(target)
                assert self.child is None
            assert len(validations) in (0, 1)
        if len(validations) == 0:
            if self.is_optional:
                self.succeeded = True
            else:
                self.succeeded = False
        else:
            self.succeeded = True
        print(self, validations, self.is_optional, self.succeeded)


class PropertyValidation(Validation):

    def __init__(self, name, validator, parent):
        super().__init__(validator)
        self.name = name
        # add this validation to the parent. this validation will be called if the parent validation succeeded:
        self.parent = parent
        parent.add(self)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.validator})>'

    def validate(self, target: h5py.Dataset):
        if not isinstance(target, h5py.Dataset):
            raise TypeError(f'PropertyValidation can only be applied to datasets, not {type(target)}')
        self.called = True
        prop = target.__getattribute__(self.name)
        is_valid = self.validator(prop)
        if is_valid:
            self.succeeded = True
        else:
            self.succeeded = self.is_optional

    @property
    def fails(self) -> int:
        return int(self.is_invalid)


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
        av = AttributeValidation(name_validator, self.parent)
        if value_validator is Ellipsis:
            value_validator = Any()
        elif isinstance(value_validator, (str, int, float)):
            value_validator = Equal(value_validator)
        AttributeValidation(value_validator, av)

    def __setitem__(self, name_validator, value_validator):
        self.add(name_validator, value_validator)

    def __getitem__(self, name_validator):
        av = AttributeValidation(name_validator, self.parent)

    # def __getitem__(self, validator) -> AttributeValidation:
    #     if not isinstance(validator, Validator):
    #         raise TypeError(f'validator must be a Validator, not {type(validator)}')
    #     return AttributeValidation(self.parent, validator)


class _BaseGroupAndDatasetValidation(Validation):

    def __init__(self,
                 validator: Validator,
                 parent: Validation):
        super().__init__(validator)
        self.parent = parent
        self.children = []

    def __repr__(self):
        return f'<{self.__class__.__name__}("{self.path}", {self.validator})>'

    @property
    def path(self):
        if self.parent is None:
            return '/'
        return '' + self.parent.path

    @property
    def attrs(self):
        return AttributeValidationManager(self)

    @property
    def fails(self):
        n = 0
        if self.is_invalid:
            n = 1
        children = copy.deepcopy(self.children)
        for child in children:
            n += child.fails
        return n

    def add_child(self, child: Validation):
        """Add a child validation object to be called after this validation succeeded

        Parameters
        ----------
        child : Validation
            The child validation object to be called after this validation succeeded
        """
        if not isinstance(child, Validation):
            raise TypeError(f'child must be a Validation, not {type(child)}')
        self.children.append(child)

    add = add_child  # alias


class DatasetValidation(_BaseGroupAndDatasetValidation):
    def validate(self, target):
        self.called = True
        validations = []
        for dataset in get_h5datasets(target):
            if self.validator(dataset.name.rsplit('/', 1)[-1]):
                validations.append(dataset)
                for child in self.children:
                    child.validate(dataset)
        if len(validations) == 0:
            if self.is_optional:
                self.succeeded = True
            else:
                self.succeeded = False
        else:
            self.succeeded = True
        print(self, validations, self.is_optional, self.succeeded)


class GroupValidation(_BaseGroupAndDatasetValidation):
    def validate(self, target):
        self.called = True
        validations = []
        for group in get_h5groups(target):
            if self.validator(group.name.strip('/')):
                validations.append(group)
                # validation succeeded:
                for child in self.children:
                    child.validate(group)
        if len(validations) == 0:
            if self.is_optional:
                self.succeeded = True
            else:
                self.succeeded = False
        else:
            self.succeeded = True
        print(self, validations, self.is_optional, self.succeeded)

    def define_dataset(self, name, **kwargs):
        dv = DatasetValidation(name, self)
        self.add(dv)
        for propname, propvalue in kwargs.items():
            pv = PropertyValidation(propname, propvalue, dv)

    def define_group(self, name: typing.Union[str, Validator]):
        """Add a group validation object"""
        if isinstance(name, str):
            name = Equal(name)
        gv = GroupValidation(name, self)
        self.add(gv)


class Layout(GroupValidation):

    def __init__(self):
        super().__init__(Equal(None), None)

    def __repr__(self):
        return f'Layout({self.children})'

    def add_group(self, name: typing.Union[str, Validator]) -> GroupValidation:
        """Add a group validation object"""
        if isinstance(name, str):
            name = Equal(name)
        gv = GroupValidation(name, self)
        self.add(gv)
        return gv

    def __getitem__(self, item: typing.Union[str, Validator]) -> Validation:
        # TODO if not yet registered, register it, otherwise return existing
        return self.add_group(item)

    def validate(self, target):
        for child in self.children:
            child.validate(target)

    @property
    def fails(self) -> int:
        n = 0
        children = copy.deepcopy(self.children)
        for child in children:
            n += child.fails
        return n
