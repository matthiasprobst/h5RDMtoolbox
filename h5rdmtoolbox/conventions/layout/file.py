import pathlib
import pickle
import typing

import h5py

from .validation import ValidationResult, ValidationResults, Validator, Equal, Any

HDF_DS_OR_GRP = typing.Union[h5py.Dataset, h5py.Group]


def flatten(list_of_lists: typing.List[typing.List]) -> typing.List:
    """flattens a list of lists"""
    # https://stackabuse.com/python-how-to-flatten-list-of-lists/
    if len(list_of_lists) == 0:
        return list_of_lists
    if isinstance(list_of_lists[0], list):
        return flatten(list_of_lists[0]) + flatten(list_of_lists[1:])
    return list_of_lists[:1] + flatten(list_of_lists[1:])


class DatasetValidator:
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
    def eval(target, **properties) -> typing.Union[typing.List[ValidationResult], None]:
        """Evaluate the properties of a dataset"""
        results = []
        if not isinstance(target, h5py.Dataset):
            return None
        for name, validator in properties.items():
            p = getattr(target, name)
            if validator(p):
                results.append(ValidationResult(True, f'"{name}" in {target.name}'))
                continue
            results.append(ValidationResult(False,
                                            f'Checking property "{name}" of dataset "{target.name}" '
                                            f'with validator "{validator.__class__.__name__}": '
                                            f'{p} != {validator.reference}'))
        return results

    def __call__(self, target: h5py.Dataset, *args, **kwargs) -> typing.Union[ValidationResult, None]:

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
                return ValidationResult(False, f'path {self.name.reference} does not exist in {target}')

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
        def visitor(_, obj):
            if isinstance(obj, h5py.Dataset):
                if parent_name_in_wildcard(obj.name.rsplit('/', 1)[0], self.parent_path):
                    return results.append(self.eval(obj, **props))

        target[base_group].visititems(visitor)
        if len(results) == 0:
            return [ValidationResult(True, f'"{self.name}" in {target}'), ]
        return results


class AttributeValidator:
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

    def __call__(self, target: HDF_DS_OR_GRP, *args, **kwargs) -> typing.Union[None, typing.List[ValidationResult]]:
        if not self.parent.parent_path.has_wildcard_suffix:
            # av_objs = [t for t, obj in target.items() if isinstance(obj, self.obj_flt)]

            if self.parent.parent_path not in target:
                if self.validator.is_optional:
                    return None
                # obj path is not in target. as validator is required, return failed validation result
                return [ValidationResult(False, f'path {self.parent.parent_path} does not exist in {target}'), ]

            if self.key not in target[self.parent.parent_path].attrs:
                if self.validator.is_optional:
                    return None
                # obj exists but the attribute not. as validator is required, return failed validation result
                return [ValidationResult(False, f'attribute "{self.key}" does not exist in {target}'), ]

            # finally, run the validation if obj and the required attribute exist:
            if not self.validator(target[self.parent.parent_path].attrs[self.key]):
                return [ValidationResult(False, f'validation failed for "{self.parent.parent_path}" in {target}'), ]

            # we made it here, so validation was successful
            return [ValidationResult(True, f'"{self.parent.parent_path}" in {target}'), ]

        base_group = self.parent.parent_path.parent
        if base_group == '':
            base_group = '/'

        results = []

        # recursively check all groups using visitor:
        def visitor(name, obj):
            if isinstance(obj, self.obj_flt):
                if self.key not in obj.attrs:
                    if self.validator.is_optional:
                        return None
                    return results.append(
                        ValidationResult(False,
                                         f'Attribute "{self.key}" is required but not found in "{name}"'))
                if not self.validator(obj.attrs[self.key]):
                    if self.validator.is_optional:
                        return None
                    return results.append(
                        ValidationResult(False,
                                         f'Attribute "{self.key}" in "{name}" does not validate')
                    )
                return results.append(ValidationResult(True, f'"{self.key}" in {target}'))

        target[base_group].visititems(visitor)
        if len(results) == 0:
            return [ValidationResult(True, f'"{self.name}" in {target}'), ]
        return results


class LayoutAttribute:

    def __init__(self, parent: typing.Union["LayoutDataset", "LayoutGroup"]):
        assert isinstance(parent, (LayoutDataset, LayoutGroup))
        self.parent = parent


class GroupLayoutAttribute(LayoutAttribute):

    def __setitem__(self, key: str, validator: Validator):
        self.parent.file.validators.append(AttributeValidator(parent=self.parent,
                                                              key=key,
                                                              validator=validator))


class DatasetLayoutAttribute(LayoutAttribute):

    def __setitem__(self, key, validator: Validator):
        self.parent.file.validators.append(AttributeValidator(parent=self.parent,
                                                              key=key,
                                                              validator=validator))


class LayoutGroup:

    def __init__(self,
                 *,
                 parent_path: typing.Union[str, "LayoutPath"],
                 file: "File"):
        self.parent_path = LayoutPath(parent_path)
        assert isinstance(file, File)
        self.file = file

    def __repr__(self):
        return f'LayoutGroup("{self.parent_path}")'

    def group(self, name=None) -> "LayoutGroup":
        """Return a new LayoutGroup object for the given group name."""
        if name is None:
            return self
        return LayoutGroup(parent_path=self.parent_path / name, file=self.file)

    def dataset(self,
                name: typing.Union[str, Validator, None] = Any(),
                shape: typing.Union[typing.Tuple[int], Validator, None] = Any(),
                ndim: typing.Union[int, Validator, Validator, None] = Any(),
                dtype: typing.Union[str, Validator, Validator, None] = Any()):
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
        if name == '*' or name is None:  # the name is not checked, thus we can use Any()
            name_validator = Any()
            parent_path = self.parent_path
        elif isinstance(name, str):
            name_validator = Equal(name)
            parent_path = self.parent_path
        elif isinstance(name, Validator):
            name_validator = name
            parent_path = self.parent_path
        else:
            raise TypeError(f'Invalid type for name: {type(name)}')

        if isinstance(shape, tuple):
            shape = Equal(shape)
        if isinstance(ndim, int):
            ndim = Equal(ndim)
        if isinstance(dtype, str):
            dtype = Equal(dtype)

        return LayoutDataset(parent_path=parent_path,
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
    parent_path: str
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
                 parent_path: "LayoutPath",
                 name: Validator,
                 shape: Validator,
                 ndim: Validator,
                 dtype: Validator,
                 file: "File"):
        assert isinstance(parent_path, LayoutPath)
        assert isinstance(name, Validator)
        assert isinstance(shape, Validator)
        assert isinstance(ndim, Validator)
        assert isinstance(dtype, Validator)
        assert isinstance(file, File)

        self.file = file
        self.parent_path = parent_path
        self.name = name
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

        self.file.validators.append(DatasetValidator(parent_path=parent_path,
                                                     file=self.file,
                                                     name=name,
                                                     shape=shape,
                                                     ndim=ndim,
                                                     dtype=dtype,
                                                     )
                                    )

    @property
    def attrs(self):
        return DatasetLayoutAttribute(self)


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

    @property
    def names(self) -> typing.List[str]:
        """Return a list of all registered layout names."""
        return list(self.layouts.keys())

    def __getitem__(self, name) -> "File":
        if name in self.layouts:
            return self.layouts[name]
        raise KeyError(f'No layout with name "{name}" found. Available layouts: {self.names}')


class File(LayoutGroup):
    """Main class for defining a layout file."""

    def __init__(self):
        super().__init__(parent_path='/', file=self)
        self.validators = []
        self._not_in = {}

    def __getitem__(self, item) -> LayoutGroup:
        return LayoutGroup(parent_path=self.parent_path / item, file=self)

    @property
    def attrs(self) -> LayoutAttribute:
        """Return a LayoutAttribute object for the root group attributes."""
        return LayoutAttribute('/', self)

    def validate(self, file: typing.Union[str, pathlib.Path, h5py.File]) -> ValidationResults:
        """Run all validators on the given file."""

        if not isinstance(file, h5py.File):
            with h5py.File(file, mode='r') as h5:
                return self.validate(h5)
        validation_results = flatten([validator(file) for validator in self.validators])
        return ValidationResults([v for v in validation_results if v is not None])

        # for k, v in self.req_attributes.items():
        #     if v['path'].has_wildcard_suffix:
        #         base_group = v['path'].parent
        #         if base_group == '':
        #             base_group = '/'
        #
        #         # recursively check all groups using visitor:
        #         def visitor(name, obj):
        #             if k not in obj.attrs:
        #                 print(f'Attribute "{k}" is required but not found in "{name}"')
        #             else:
        #                 if not v['validator'](obj.attrs[k]):
        #                     print(f'Attribute "{k}" in "{name}" does not validate')
        #
        #         file[base_group].visititems(visitor)
        #         continue
        #     if v['path'] not in file:
        #         print(f'Attribute "{k}" is required but not found in "{v["path"]}"')
        #         continue
        #     if k not in file[v['path']].attrs:
        #         print(f'Attribute "{k}" is required but not found in "{v["path"]}"')
        #         continue
        #     if not v['validator'](file[v['path']].attrs[k]):
        #         print(f'Attribute "{k}" in "{v["path"]}" does not validate')
        #
        # for k, v in self.opt_attributes.items():
        #     if v['path'] not in file:
        #         continue
        #     if k not in file[v['path']].attrs:
        #         continue
        #     if not v['validator'](file[v['path']].attrs[k]):
        #         print(f'Attribute "{k}" in "{v["path"]}" does not validate')

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

    @property
    def Registry(self) -> LayoutRegistry:
        """Return the Registry interface class."""
        return LayoutRegistry()
