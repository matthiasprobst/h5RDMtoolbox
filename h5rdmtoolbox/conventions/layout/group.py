import typing

import h5py

from . import validations
from .path import LayoutPath


class GroupValidation(validations.Validation):
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


class Group:

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

    def group(self, name=None) -> "LayoutGroup":
        """Return a new LayoutGroup object for the given group name."""
        if name is None:
            return self
        path = self.path / name
        self.file.validators.add(GroupValidation(path))
        return Group(path=path, file=self.file)

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
