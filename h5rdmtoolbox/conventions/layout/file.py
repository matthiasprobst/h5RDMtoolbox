import pathlib
import pickle
from typing import Union, List, Callable, Dict

import h5py

from .compare import Equal, Regex, AnyString
from .validation import ValidationResult, ValidationResults


class DatasetValidator:
    """Validates a dataset

    Parameters
    ----------
    prop : str
        The property to check
    name : str
        The name of the dataset
    validation : Callable
        The validation function
    """

    def __init__(self,
                 parent: str,
                 file: "File",
                 name, shape, ndim, dtype):
        self.parent = parent
        # properties to check:
        self.file = file
        self.name = name
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

    def _eval(self, target, **properties):
        results = []
        if not isinstance(target, h5py.Dataset):
            return None
        for name, validation in properties.items():
            print(target, target.name)
            p = getattr(target, name)
            if validation(p):
                results.append(ValidationResult(True, f'"{name}" in {target.name}'))
                continue
            results.append(ValidationResult(False,
                                            f'Checking property "{name}" of dataset "{target.name}" '
                                            f'with validator "{validation.__class__.__name__}": '
                                            f'{p} != {validation.reference}'))
        return results

    def __call__(self, target: h5py.Dataset, *args, **kwargs) -> Union[ValidationResult, None]:

        props = {}
        for k, v in zip(('shape', 'ndim', 'dtype'),
                        (self.shape, self.ndim, self.dtype)):
            if v.reference is not None:
                props[k] = v

        if not self.parent.has_widcard_suffix:
            # TODO for Regex, the name must not necessarily be contained in the file
            name = self.parent / self.name.reference
            if isinstance(self.name, Equal):
                if name not in target:
                    if name in self.file._not_in:
                        if target in self.file._not_in[self.name]:
                            return None  # already checked if target exist, dont do again
                    if name not in self.file._not_in:
                        self.file._not_in[name] = [target, ]
                    else:
                        self.file._not_in[name].append(target)
                    return ValidationResult(False, f'path {name} does not exist in {target}')
                return self._eval(target[name], **props)
            elif isinstance(self.name, Regex):
                if name in target:
                    raise NotImplementedError('Regex comparison not implemented for datasets')

        base_group = self.parent.parent
        if base_group == '':
            base_group = '/'

        results = []

        def parent_name_in_wildcard(obj_name, wildcard_name):
            """Check if object name is in wildcard name"""
            assert wildcard_name.has_widcard_suffix
            if obj_name == '':
                obj_name = '/'
            obj_pathlib = pathlib.Path(obj_name)
            wildcard_pathlib = pathlib.Path(wildcard_name.parent)
            # check if obj_pathlib is in wildcard_pathlib:
            return wildcard_pathlib in obj_pathlib.parents or obj_pathlib == wildcard_pathlib

        # recursively check all groups using visitor:
        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                if parent_name_in_wildcard(obj.name.rsplit('/', 1)[0], self.parent):
                    return results.append(self._eval(obj, **props))

        target[base_group].visititems(visitor)
        if len(results) == 0:
            return [ValidationResult(True, f'"{self.name}" in {target}'), ]
        return results


class AttributeValidator:
    def __init__(self, obj: str, name: str, key: str, validation: Callable):
        self.obj = obj
        self.name = name
        self.key = key
        self.validation = validation

    def __call__(self, target: Union[h5py.Dataset, h5py.Group], *args, **kwargs) -> List[
        ValidationResult]:
        if not self.name.has_widcard_suffix:
            if self.name not in target:
                return ValidationResult(False, f'path {self.name} does not exist in {target}')
            if self.key not in target[self.name].attrs:
                return ValidationResult(False, f'attribute "{self.key}" does not exist in {target}')
            if not self.validation(target[self.name].attrs[self.key]):
                return ValidationResult(False, f'validation failed for "{self.name}" in {target}')
            return ValidationResult(True, f'"{self.name}" in {target}')

        base_group = self.name.parent
        if base_group == '':
            base_group = '/'

        results = []

        # recursively check all groups using visitor:
        def visitor(name, obj):
            if self.obj == 'group':
                obj_cls = h5py.Group
            elif self.obj == 'dataset':
                obj_cls = h5py.Dataset
            if isinstance(obj, obj_cls):
                if self.key not in obj.attrs:
                    return results.append(
                        ValidationResult(False,
                                         f'Attribute "{self.key}" is required but not found in "{name}"'))
                if not self.validation(obj.attrs[self.key]):
                    return results.append(
                        ValidationResult(False,
                                         f'Attribute "{self.key}" in "{name}" does not validate')
                    )
                return results.append(ValidationResult(True, f'"{self.name}" in {target}'))

        target[base_group].visititems(visitor)
        if len(results) == 0:
            return [ValidationResult(True, f'"{self.name}" in {target}'), ]
        return results


class LayoutAttribute:

    def __init__(self, name, file: "File"):
        self.name = name
        self.file = file


class GroupLayoutAttribute(LayoutAttribute):

    def __setitem__(self, key: str, validation: Callable):
        self.file.validators.append(AttributeValidator(obj='group', name=self.name, key=key, validation=validation))


class DatasetLayoutAttribute(LayoutAttribute):

    def __setitem__(self, key, value):
        self.file.validators.append(AttributeValidator(obj='dataset', name=self.name, key=key, validation=value))


class LayoutGroup:

    def __init__(self, name, file: "File"):
        self.name = LayoutPath(name)
        self.file = file

    def __repr__(self):
        return f'LayoutGroup("{self.name}")'

    def group(self, name=None) -> "LayoutGroup":
        """Return a new LayoutGroup object for the given group name."""
        if name is None:
            return self
        return LayoutGroup(self.name / name, self.file)

    def dataset(self, name=None, shape=None, ndim=None, dtype=None):
        """Return a new LayoutDataset object for the given dataset name."""
        if name is None:
            return LayoutDataset(self.name, shape, ndim, dtype, self.file)
        return LayoutDataset(LayoutPath(f'{self.name}/{name}'), shape, ndim, dtype, self.file)

    @property
    def attrs(self):
        return GroupLayoutAttribute(self.name, self.file)


class LayoutDataset:
    """A dataset in a layout file.

    Parameters
    ----------
    name : str or None
        The (full) name of the dataset. Name may be None, then
        name will not be checked
    shape : tuple or None
        The shape of the dataset
    ndim : int or None
        The dimension of the dataset
    dtype : str or None
        The dtype of the dataset
    file : File
        The File object
    """

    def __init__(self, name, shape, ndim, dtype, file: "File"):
        self.file = file
        if name[-1] == '*':
            parent = name
            dataset_name = None
        elif name is None:
            parent = name
            dataset_name = None
        else:
            parent = name.parent
            dataset_name = name.name

        self.name = name
        self.shape = shape
        self.ndim = ndim
        self.dtype = dtype

        self.file.validators.append(DatasetValidator(parent=parent,
                                                     file=self.file,
                                                     name=Equal(dataset_name),
                                                     shape=Equal(shape),
                                                     ndim=Equal(ndim),
                                                     dtype=Equal(dtype),
                                                     )
                                    )

    @property
    def attrs(self):
        return DatasetLayoutAttribute(self.name, self.file)


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
    def parents(self) -> List[str]:
        return self.split('/')

    @property
    def has_widcard_suffix(self):
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
    def build_defaults() -> Dict:
        """Build the default layouts."""
        # pre-defined layouts:
        TbxLayout = File()
        TbxLayout.attrs['__h5rdmtoolbox__'] = '__version of this package'
        TbxLayout.attrs['title'] = AnyString

        _defaults = {'tbx': TbxLayout}
        return _defaults

    def __init__(self):
        self.layouts = self.build_defaults()

    @property
    def names(self) -> List[str]:
        """Return a list of all registered layout names."""
        return list(self.layouts.keys())

    def __getitem__(self, name) -> "File":
        if name in self.layouts:
            return self.layouts[name]
        raise KeyError(f'No layout with name "{name}" found. Available layouts: {self.names}')


class File(LayoutGroup):
    """Main class for defining a layout file."""

    def __init__(self):
        super().__init__('/', self)
        self.validators = []
        self._not_in = {}

    def __getitem__(self, item) -> LayoutGroup:
        return LayoutGroup(self.name / item, self)

    @property
    def attrs(self) -> LayoutAttribute:
        """Return a LayoutAttribute object for the root group attributes."""
        return LayoutAttribute('/', self)

    def validate(self, file: Union[str, pathlib.Path, h5py.File]) -> ValidationResults:
        """Run all validators on the given file."""

        def flatten(list_of_lists):
            # https://stackabuse.com/python-how-to-flatten-list-of-lists/
            if len(list_of_lists) == 0:
                return list_of_lists
            if isinstance(list_of_lists[0], list):
                return flatten(list_of_lists[0]) + flatten(list_of_lists[1:])
            return list_of_lists[:1] + flatten(list_of_lists[1:])

        if not isinstance(file, h5py.File):
            with h5py.File(file, mode='r') as h5:
                return self.validate(h5)
        validation_results = flatten([validator(file) for validator in self.validators])
        return ValidationResults([v for v in validation_results if v is not None])

        # for k, v in self.req_attributes.items():
        #     if v['path'].has_widcard_suffix:
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

    def save(self, filename: Union[str, pathlib.Path], overwrite=False) -> None:
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
