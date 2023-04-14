import typing

import h5py

from . import properties
from . import validators
from .path import LayoutPath
from .validations import Validation


class Dataset:
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
                 name: validators.Validator,
                 file: "File"):
        assert isinstance(path, LayoutPath)
        assert isinstance(name, validators.Validator)
        assert isinstance(file, file.File)

        self.file = file
        self.path = path
        self.name = name

        name_val = DatasetValidation(parent_path=path,
                                     file=self.file,
                                     name=name)
        self.file.validators.add(name_val)

    @property
    def attrs(self):
        from .attrs import LayoutAttributeManager
        return LayoutAttributeManager(self)

    def __repr__(self):
        return f'<LayoutDataset("{self.path}")>'


class DatasetValidator(validators.Validator):
    """Behaves like a Validator but is not a real one"""

    def __init__(self,
                 reference: typing.Dict,
                 optional: bool):
        self.reference = reference
        self._optional = optional
        self.called = False
        self.candidates = []

    def validate(self, _, target: h5py.Group):
        # check name:
        dataset_objects = [t for t in target.values() if isinstance(t, h5py.Dataset)]

        if len(dataset_objects) == 0 and self.is_optional:
            return True

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
                 name: validators.Validator,
                 shape: validators.Validator):
        from .group import Group
        assert isinstance(parent, Group)
        assert isinstance(name, validators.Validator)
        assert isinstance(shape, validators.Validator)
        self.parent = parent
        self.validator = DatasetValidator(reference={'name': name, 'shape': shape}, optional=False)
        self.candidates = []  # special for this class as compared to the other validator classes

    def __repr__(self):
        return f'{self.__class__.__name__}(parent={self.parent.path}")'

    def visititems(self, target: h5py.Group) -> typing.List[validators.Validator]:
        """Recursively visit all items in the target and call the method `validate`"""
        validators = []

        def visitor(_, obj):
            if isinstance(obj, h5py.Group):
                validators.append(self.validator(obj))

        target.visititems(visitor)
        validators.append(self.validator(value=target))
        return validators

    def __call__(self, target: h5py.Group) -> typing.Union[
        None, validators.Validator, typing.List[validators.Validator]]:
        """called by Layout.validate()"""
        assert isinstance(target, h5py.Group)
        rec = self.parent.path.has_wildcard_suffix
        if rec:
            self.validator._optional = True
            # call the validator on each object in the group
            return self.visititems(target=target)
        return self.validator(value=target)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.parent.path == other.parent.path and \
               self.name == other.name and \
               self.shape == other.shape and \
               self.ndim == other.ndim and \
               self.dtype == other.dtype

    def __ne__(self, other):
        return not self.__eq__(other)
