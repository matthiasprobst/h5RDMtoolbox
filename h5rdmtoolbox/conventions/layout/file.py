import abc
import inspect
import pathlib
import pickle
import typing

import h5py

from .utils import flatten
from .validation import Validator, Any, Equal
from .validation.attribute import AttributeEqual, AnyAttribute
from .validation.results import ValidationResults

# from .validation import (GroupNotExist, ValidationResults, Validator, Equal,
#                          HDFObjectExist, AttributeEqual, Any, AnyAttribute)

HDF_DS_OR_GRP = typing.Union[h5py.Dataset, h5py.Group]


class _Validator(abc.ABC):

    @abc.abstractmethod
    def __eq__(self, other):
        pass

    def __ne__(self, other):
        return not self.__eq__(other)


class DatasetValidator(_Validator):
    """Validates a dataset

    Parameters
    ----------
    prop : str
        The property to check
    name : Validator
        Validator for the base name of the dataset
    shape : Validator
        Validator for the shape of the dataset
    ndim : Validator
        Validator for the number of dimensions of the dataset
    dtype : Validator
        Validator for the data type of the dataset
    """

    def __init__(self,
                 *,
                 parent_path: "LayoutPath",
                 file: "File",
                 name: Validator,
                 shape: Validator,
                 ndim: Validator,
                 dtype: Validator):
        assert isinstance(parent_path, LayoutPath)
        assert isinstance(name, Validator)
        assert isinstance(shape, Validator)
        assert isinstance(ndim, Validator)
        assert isinstance(dtype, Validator)
        self.parent_path = parent_path
        # properties to check:
        self.file = file
        self.name = name
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

    @staticmethod
    def eval(target, **properties) -> typing.Union[ValidationResults, None]:
        """Evaluate the properties of a dataset"""
        results = ValidationResults()
        if not isinstance(target, h5py.Dataset):
            return None
        for name, validator in properties.items():
            p = getattr(target, name)
            if validator(p):
                results.add(validator, None)
                continue
            results.add(validator)

        return results

    def __repr__(self):
        return f'{self.__class__.__name__}(parent={self.parent_path}, name="{self.name}", shape={self.shape}, ' \
               f'ndim={self.ndim}, dtype={self.dtype})'

    def __call__(self, target: h5py.Dataset, *args, **kwargs) -> typing.Union[ValidationResults, None]:
        results = []
        props = {}
        for k, v in zip(('shape', 'ndim', 'dtype'),
                        (self.shape, self.ndim, self.dtype)):
            if v.reference is not None:
                props[k] = v

        if not self.parent_path.has_wildcard_suffix:
            av_datasets = [t for t, obj in target.items() if isinstance(obj, h5py.Dataset)]

            # run over all datasets. and collect the successes of the __call__ method of the validator
            # optional validators except if there has not been a success
            name_successes = {name: self.name(name) for name in av_datasets}
            if not any(name_successes.values()) and not self.name.is_optional:
                # non-optional validator failed
                return results.add(GroupNotExist(self.name.reference, target))

            # for those dataset that succeeded the name check, now check the other properties:
            results = flatten([self.eval(target[k], **props) for k, v in name_successes.items()])
            return results

        base_group = self.parent_path.parent
        if base_group == '':
            base_group = '/'

        results = []

        def parent_name_in_wildcard(obj_name, wildcard_name):
            """Check if object name is in wildcard name"""
            assert wildcard_name.has_wildcard_suffix
            if obj_name == '':
                obj_name = '/'
            obj_pathlib = pathlib.Path(obj_name)
            wildcard_pathlib = pathlib.Path(wildcard_name.parent)
            # check if obj_pathlib is in wildcard_pathlib:
            return wildcard_pathlib in obj_pathlib.parents or obj_pathlib == wildcard_pathlib

        # recursively check all groups using visitor:
        def visitor(_, obj: HDF_DS_OR_GRP):
            """function called on each object in the HDF5 file"""
            if isinstance(obj, h5py.Dataset):
                if parent_name_in_wildcard(obj.name.rsplit('/', 1)[0], self.parent_path):
                    return results.append(self.eval(obj, **props))

        if base_group not in target:
            results.append(HDFObjectExist(base_group, target.name), GroupNotExist(base_group, target.name))
        else:
            target[base_group].visititems(visitor)
        return results

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.parent_path == other.parent_path and self.name == other.name and self.shape == other.shape \
               and self.ndim == other.ndim and self.dtype == other.dtype

    def __ne__(self, other):
        return not self.__eq__(other)


class GroupValidation(_Validator):
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


class AttributeValidator(_Validator):
    """Validation class for attributes"""

    def __init__(self,
                 parent: typing.Union["LayoutDataset", "LayoutGroup"],
                 key: str,
                 validator: typing.Callable):
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
            validators.append(self.validator(key, obj))

        target.visititems(visitor)
        return validators

    def __call__(self, target: HDF_DS_OR_GRP, *args, **kwargs) -> typing.Union[None, Validator, typing.List[Validator]]:
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            # call the validator on each object in the group
            return self.visititems(key=self.key, target=target)
        return self.validator(key=self.key, target=target)

        # results = ValidationResults()
        # if not self.parent.path.has_wildcard_suffix:
        #     # av_objs = [t for t, obj in target.items() if isinstance(obj, self.obj_flt)]
        #
        #     if self.parent.path not in target:
        #         if self.validator.is_optional:
        #             return None
        #         # obj path is not in target. as validator is required, return failed validation result
        #         return results.add(self.validator)
        #
        #     results.add(self.validator(target))
        #     return results
        #
        # base_group = self.parent.path.parent
        # if base_group == '':
        #     base_group = '/'
        #
        # results = ValidationResults()
        #
        # # recursively check all groups using visitor:
        # def visitor(_, obj):
        #     if isinstance(obj, self.obj_flt):
        #         if self.key not in obj.attrs:
        #             if self.validator.is_optional:
        #                 return None
        #             return results.add(self.validator)
        #         if not self.validator(obj.attrs[self.key]):
        #             if self.validator.is_optional:
        #                 return None
        #             return results.add(self.validator)
        #         return results.append(self.validator)
        #
        #
        # # TODO think about this: validator(<value>, rec=self.parent.path.has_wildcard_suffix) --> validator handles recursion
        # exist_validator = HDFObjectExist(base_group)
        # if not exist_validator(target):
        #     results.add(exist_validator)
        # else:
        #     target[base_group].visititems(visitor)
        # return results


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
        attrval = AttributeValidator(parent=self.parent,
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

    def dataset(self,
                name: typing.Union[str, Validator, None] = Any,
                shape: typing.Union[typing.Tuple[int], Validator, None] = Any,
                ndim: typing.Union[int, Validator, Validator, None] = Any,
                dtype: typing.Union[str, Validator, Validator, None] = Any):
        """Return a new LayoutDataset object for the given dataset name.

        Parameters
        ----------
        name : None, str or Validator
            The basename of the dataset. If None, the dataset is not checked, the validation
            is applied on any dataset in the group. This is equal to passing the validator `AnyString`.
            If a string, only datasets with the given basename are checked.
            If a Validator is passed, the validator is applied to the basename of the dataset.

            .. note::

                Different to h5py syntax, the dataset name here is the basename of the dataset.
                The dataset must be addressed relative to the group. Thus, the basename must not
                contain a slash.

        """
        if name == '*' or name is None:  # the name is not checked, thus we can use Any
            name_validator = Any
            path = self.path
        elif isinstance(name, str):
            name_validator = Equal(name)
            path = self.path
        elif isinstance(name, Validator):
            name_validator = name
            path = self.path
        else:
            raise TypeError(f'Invalid type for name: {type(name)}')

        if isinstance(shape, tuple):
            shape = Equal(shape)
        if isinstance(ndim, int):
            ndim = Equal(ndim)
        if isinstance(dtype, str):
            dtype = Equal(dtype)

        return LayoutDataset(path=path,
                             name=name_validator,
                             shape=shape,
                             ndim=ndim,
                             dtype=dtype,
                             file=self.file)

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
    shape : tuple or None
        The shape of the dataset
    ndim : int or None
        The dimension of the dataset
    dtype : str or None
        The dtype of the dataset
    file : File
        The File object
    """

    def __init__(self,
                 *,
                 path: "LayoutPath",
                 name: Validator,
                 shape: Validator,
                 ndim: Validator,
                 dtype: Validator,
                 file: "File"):
        assert isinstance(path, LayoutPath)
        assert isinstance(name, Validator)
        assert isinstance(shape, Validator)
        assert isinstance(ndim, Validator)
        assert isinstance(dtype, Validator)
        assert isinstance(file, File)

        self.file = file
        self.path = path
        self.name = name
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

        attrval = DatasetValidator(parent_path=path,
                                   file=self.file,
                                   name=name,
                                   shape=shape,
                                   ndim=ndim,
                                   dtype=dtype,
                                   )
        self.file.validators.add(attrval)

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

    def __getitem__(self, item):
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
