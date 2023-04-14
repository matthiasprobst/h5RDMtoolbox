import copy
import pathlib
import pickle
import typing

import h5py

from . import registry
from .attrs import LayoutAttributeManager
from .results import ValidationResults
from .validations import Validation
from .validators import Validator
from . import utils

HDF_DS_OR_GRP = typing.Union[h5py.Dataset, h5py.Group]


class ValidationList:
    """A list of validators."""

    def __init__(self):
        self._validations = []

    def __repr__(self):
        validator_str = ', '.join(k.__repr__() for k in self._validations)
        return f'[{validator_str}]'

    def __len__(self):
        return len(self._validations)

    def __contains__(self, item: Validator):
        for v in self._validations:
            if v == item:
                return True
        return False

    def add(self, validation: Validation):
        """Append a validation object to the list if it is not already in the list."""
        if not isinstance(validation, Validation):
            raise TypeError(f'validator must be a Validation, not {type(validation)}')
        if validation.validator is None:
            raise ValueError('Cannot add Validator object with no valid validator method (validator is None).')

        for v in self._validations:
            if v.parent == validation.parent and v.validator == validation.validator:
                return
        self._validations.append(validation)

    def remove(self, validator: Validator) -> None:
        """Removes a validator from the object/list"""
        new_validators = []
        for v in self._validations:
            if v != validator:
                new_validators.append(v)
        self._validations = new_validators

    def __getitem__(self, item) -> "Validation":
        return self._validations[item]


class Layout:
    """Main class for defining a layout file."""

    def __init__(self):
        self.validations = ValidationList()
        self._not_in = {}

    def __getitem__(self, item) -> "Group":
        from .group import Group
        if item == '/':
            return Group(path='/', file=self)
        if item.startswith('/'):
            return Group(path=item, file=self)
        return Group(path=f'/{item}', file=self)

    def __repr__(self) -> str:
        if len(self.validations) == 0:
            return f'<Layout File (empty)>'
        rstr = f'<Layout File ({len(self.validations)} validators):'
        for i, v in enumerate(self.validations):
            rstr += f'\n [{i}] {v}'
        rstr += '>'
        return rstr

    @property
    def attrs(self) -> LayoutAttributeManager:
        """Return a LayoutAttributeManager object for the root group attributes."""
        from .group import Group
        return LayoutAttributeManager(Group(path='/', file=self))

    def validate(self, file: typing.Union[str, pathlib.Path, h5py.File]) -> ValidationResults:
        """Run all validators on the given file."""

        if not isinstance(file, h5py.File):
            with h5py.File(file, mode='r') as h5:
                return self.validate(h5)
        # make deep copies of the validations and perform validation:
        results = utils.flatten([validation(file) for validation in copy.deepcopy(self.validations)])
        return ValidationResults(results)
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
    def Registry(cls) -> registry.LayoutRegistry:
        """Return the Registry interface class."""
        return registry.LayoutRegistry()
