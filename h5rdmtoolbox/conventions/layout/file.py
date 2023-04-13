import abc
import inspect
import pathlib
import pickle
import typing

import h5py

from .validation import Validator, Any, Equal
from .validation.attribute import AttributeEqual, AnyAttribute, AttributeValidator
from .validation.results import ValidationResults
from .validation import properties

# from .validation import (GroupNotExist, ValidationResults, Validator, Equal,
#                          HDFObjectExist, AttributeEqual, Any, AnyAttribute)

HDF_DS_OR_GRP = typing.Union[h5py.Dataset, h5py.Group]


class Validation(abc.ABC):
    """Abstract class to host validators. This class is used to call the validators and
    perform its validation."""

    @abc.abstractmethod
    def __eq__(self, other):
        pass

    def __ne__(self, other):
        return not self.__eq__(other)


class DatasetValidator(Validator):
    """Behaves like a Validator but is not a real one"""

    def __init__(self,
                 reference: typing.Dict,
                 optional: bool):
        self.reference = reference
        self._optional = optional
        self.called = False
        self.candidates = []

    def validate(self, target: h5py.Group):
        # check name:
        dataset_objects = [t for t in target.values() if isinstance(t, h5py.Dataset)]

        candidates = []
        wrapper = properties.PropertyValidatorWrapper()
        # check properties:
        for ds in dataset_objects:
            # check properties:
            _passed = []
            for prop, validator in self.reference.items():
                _passed.append(wrapper(property_name=prop, validator=validator)(ds).passed)
            if all(_passed):
                candidates.append(ds)

        # now we found candidates for which the name and all properties are validated.
        self.candidates = [ds.name for ds in set(candidates)]
        return len(self.candidates) > 0


class DatasetValidation(Validation):
    """Validates a dataset

    Parameters
    ----------
    prop : str
        The property to check
    name : Validator
        Validator for the base name of the dataset
    """

    def __init__(self,
                 parent: "LayoutGroup",
                 name: Validator,
                 shape: Validator):
        assert isinstance(parent, LayoutGroup)
        assert isinstance(name, Validator)
        assert isinstance(shape, Validator)
        self.parent = parent
        self.validator = DatasetValidator(reference={'name': name, 'shape': shape}, optional=False)
        self.candidates = []  # special for this class as compared to the other validator classes

    def __repr__(self):
        return f'{self.__class__.__name__}(parent={self.parent_path}, name="{self.name}")'

    def visititems(self, target: h5py.Group) -> typing.List[Validator]:
        """Recursively visit all items in the target and call the method `validate`"""
        validators = []

        def visitor(_, obj):
            if isinstance(obj, h5py.Group):
                validators.append(self.validator(obj))

        target.visititems(visitor)
        return validators

    def __call__(self, target: h5py.Group) -> typing.Union[None, Validator, typing.List[Validator]]:
        """called by File.validate()"""
        assert isinstance(target, h5py.Group)
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(key=self.key, target=target)
        return self.validator(value=target)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.parent_path == other.parent_path and self.name == other.name and self.shape == other.shape \
               and self.ndim == other.ndim and self.dtype == other.dtype

    def __ne__(self, other):
        return not self.__eq__(other)


class GroupValidation(Validation):
    """Group validation class. Only validates existence of a group"""

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f'{self.__class__.__name__}(path="{self.path}")'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self.path) == str(other.path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __call__(self, target: h5py.Group, *args, **kwargs):
        results = []
        has_wildcard = '*' in self.path
        if has_wildcard:
            return None
            # TODO in future: add COUNT(<num>) to lay[*].group('device') = COUNT(1) to specify that "device" must appear at least once. otherwise wildcard has no effect as it is optional anyways

            # split = self.path.split('*')
            # if len(split) != 2:
            #     raise RuntimeError('It seems that there are too many wildcards in the path. Only one is allowed: '
            #                        f'{self.path}')
            # parent_path, group_name = split
            # group_name = group_name.strip('/')
            #
            # if parent_path in target:
            #     # recursively run through target and check if group_name exists!
            #     class visitor(_, obj):
            #         if isinstance(obj, h5py.Group):
            #             if group_name in obj:
            #                 if
            #                 results.append(ValidationResult(True, f'Group {self.path} exists in {target}'))
            #     target[parent_path].visititems(visitor)

        exist_validator = HDFObjectExist(self.path)
        results.add(exist_validator)
        return results


class AttributeValidation(Validation):
    """Validation class for attributes"""

    def __init__(self,
                 parent: typing.Union["LayoutDataset", "LayoutGroup"],
                 key: str,
                 validator: Validator):
        assert isinstance(parent, (LayoutDataset, LayoutGroup))
        self.parent = parent
        if isinstance(self.parent, LayoutGroup):
            self.obj_flt = h5py.Group
        elif isinstance(self.parent, LayoutDataset):
            self.obj_flt = h5py.Dataset
        else:
            raise TypeError('parent must be either a "GroupLayoutAttribute" or a "DatasetLayoutAttribute" but '
                            f'is {type(self.parent)}')
        self.key = key
        self.validator = validator

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.parent == other.parent and self.key == other.key and self.validator == other.validator

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f'{self.__class__.__name__}(path="{self.parent.path}", key="{self.key}", ' \
               f'validator={self.validator.__repr__()})'

    def visititems(self, key, target) -> typing.List[Validator]:
        """Recursively visit all items in the target and call the method `validate`"""
        validators = []

        def visitor(_, obj):
            if isinstance(obj, self.obj_flt):
                validators.append(self.validator(key, obj))

        target.visititems(visitor)
        return validators

    def __call__(self, target: h5py.Group) -> typing.Union[None, Validator, typing.List[Validator]]:
        """called by File.validate()"""
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(key=self.key, target=target)
        return self.validator(key=self.key, target=target)


class LayoutAttribute:
    """Base class for layout attributes."""

    def __init__(self, parent: typing.Union["LayoutDataset", "LayoutGroup"]):
        assert isinstance(parent, (LayoutDataset, LayoutGroup))
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
        if inspect.isclass(validator):
            raise TypeError('validator must be an instance of a Validator, not a class')
        if isinstance(validator, Any):
            validator = AnyAttribute()
        elif isinstance(validator, (float, int, str)):
            validator = AttributeEqual(validator)
        attrval = AttributeValidation(parent=self.parent,
                                      key=key,
                                      validator=validator)
        self.parent.file.validators.add(attrval)
        return attrval


class GroupLayoutAttribute(LayoutAttribute):
    """Layout attribute for groups."""


class DatasetLayoutAttribute(LayoutAttribute):
    """Layout attribute for datasets."""


class LayoutGroup:

    def __init__(self,
                 *,
                 path: typing.Union[str, "LayoutPath"],
                 file: "File"):
        self.path = LayoutPath(path)
        assert isinstance(file, File)
        self.file = file

    def __repr__(self):
        return f'LayoutGroup("{self.path}")'

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return str(self.path) == str(other.path)

    def __ne__(self, other):
        return not self.__eq__(other)

    def group(self, name=None) -> "LayoutGroup":
        """Return a new LayoutGroup object for the given group name."""
        if name is None:
            return self
        path = self.path / name
        self.file.validators.add(GroupValidation(path))
        return LayoutGroup(path=path, file=self.file)

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
            name_validator = Any()
        elif isinstance(name, str):  # explicit name is given, this dataset must exist!
            name_validator = Equal(name)
        elif isinstance(name, Validator):
            name_validator = name
        else:
            raise TypeError(f'Invalid type for name: {type(name)}')

        if shape is None:
            shape_validator = Any()
        elif isinstance(shape, Validator):
            shape_validator = shape
        else:
            shape_validator = Equal(shape)

        dataset_validation = DatasetValidation(parent=self,
                                               name=name_validator,
                                               shape=shape_validator)
        self.file.validators.add(dataset_validation)
        return dataset_validation

    @property
    def attrs(self):
        """Return a new GroupLayoutAttribute object for the given group name."""
        return GroupLayoutAttribute(self)


class LayoutDataset:
    """A dataset in a layout file.

    Parameters
    ----------
    path: str
        The parent path of the dataset
    name : str or None
        The basename fo the dataset
    file : File
        The File object
    """

    def __init__(self,
                 *,
                 path: "LayoutPath",
                 name: Validator,
                 file: "File"):
        assert isinstance(path, LayoutPath)
        assert isinstance(name, Validator)
        assert isinstance(file, File)

        self.file = file
        self.path = path
        self.name = name

        name_val = DatasetValidation(parent_path=path,
                                     file=self.file,
                                     name=name)
        self.file.validators.add(name_val)

    @property
    def attrs(self):
        return DatasetLayoutAttribute(self)

    def __repr__(self):
        return f'<LayoutDataset("{self.path}")>'


class LayoutPath(str):
    """A path in a HDF5 file used in the Layout class."""

    @property
    def name(self) -> str:
        return self.rsplit('/', 1)[-1]

    @property
    def parent(self) -> str:
        p = LayoutPath(self.rsplit('/', 1)[0])
        if p == '':
            return '/'
        return p

    @property
    def parents(self) -> typing.List[str]:
        return self.split('/')

    @property
    def has_wildcard_suffix(self):
        """Return True if the path ends with a wildcard suffix."""
        return self[-1] == '*'

    def __add__(self, other) -> "LayoutPath":
        if len(other) == 0:
            raise ValueError('Other name must not be empty')
        if other == '/':
            return self
        if other[0] == '/':
            other = other[1:]
        if self == '/':
            return LayoutPath(f'{self}{other}')
        return LayoutPath(f'{self}/{other}')

    def __truediv__(self, other):
        return self.__add__(other)


_defaults = {}


class LayoutRegistry:
    """Registry interface class for File objects."""

    @staticmethod
    def build_defaults() -> typing.Dict:
        """Build the default layouts."""
        # pre-defined layouts:
        TbxLayout = File()
        TbxLayout.attrs['__h5rdmtoolbox__'] = '__version of this package'
        TbxLayout.attrs['title'] = Any()

        _defaults = {'tbx': TbxLayout}
        return _defaults

    def __init__(self):
        self.layouts = self.build_defaults()

    def __repr__(self):
        names = ','.join(f'"{k}"' for k in self.layouts.keys())
        return f'LayoutRegistry({names},)'

    @property
    def names(self) -> typing.List[str]:
        """Return a list of all registered layout names."""
        return list(self.layouts.keys())

    def __getitem__(self, name) -> "File":
        if name in self.layouts:
            return self.layouts[name]
        raise KeyError(f'No layout with name "{name}" found. Available layouts: {self.names}')


class ValidatorList:
    """A list of validators."""

    def __init__(self):
        self._validators = []

    def __repr__(self):
        validator_str = ', '.join(k.__repr__() for k in self._validators)
        return f'[{validator_str}]'

    def __len__(self):
        return len(self._validators)

    def __contains__(self, item: Validator):
        for v in self._validators:
            if v == item:
                return True
        return False

    def add(self, validator: Validator):
        """Append a validator to the list if it is not already in the list."""
        for v in self._validators:
            if v == validator:
                return
        self._validators.append(validator)

    def remove(self, validator: Validator) -> None:
        """Removes a validator from the object/list"""
        new_validators = []
        for v in self._validators:
            if v != validator:
                new_validators.append(v)
        self._validators = new_validators

    def __getitem__(self, item) -> "Validation":
        return self._validators[item]


class File(LayoutGroup):
    """Main class for defining a layout file."""

    def __init__(self):
        super().__init__(path='/', file=self)
        self.validators = ValidatorList()
        self._not_in = {}

    def __getitem__(self, item) -> LayoutGroup:
        return LayoutGroup(path=self.path / item, file=self)

    def __repr__(self) -> str:
        if len(self.validators) == 0:
            return f'<Layout File (empty)>'
        rstr = f'<Layout File ({len(self.validators)} validators):'
        for i, v in enumerate(self.validators):
            rstr += f'\n [{i}] {v}'
        rstr += '>'
        return rstr

    @property
    def attrs(self) -> LayoutAttribute:
        """Return a LayoutAttribute object for the root group attributes."""
        return GroupLayoutAttribute(LayoutGroup(path='/', file=self))

    def validate(self, file: typing.Union[str, pathlib.Path, h5py.File]) -> ValidationResults:
        """Run all validators on the given file."""

        if not isinstance(file, h5py.File):
            with h5py.File(file, mode='r') as h5:
                return self.validate(h5)
        return ValidationResults.concatenate_results([validator(file) for validator in self.validators])
        # return ValidationResults([v for v in validation_results if v is not None])

    def save(self, filename: typing.Union[str, pathlib.Path], overwrite=False) -> None:
        """Save the File to a file.

        Parameters
        ----------
        filename: str or pathlib.Path
            The filename to save the File to.
        overwrite: bool
            If True, overwrite existing files.

        Raises
        ------
        FileExistsError
            If the file already exists and overwrite is False.
        """
        filename = pathlib.Path(filename)
        if filename.exists() and not overwrite:
            raise FileExistsError(f'File "{filename}" already exists.')
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(filename) -> "File":
        """Load a File from a file."""
        with open(filename, 'rb') as f:
            return pickle.load(f)

    @classmethod
    def Registry(cls) -> LayoutRegistry:
        """Return the Registry interface class."""
        return LayoutRegistry()
