"""Core module for the layout convention."""
import copy
import h5py
import typing
import warnings

from . import validation
from .validators import Validator, Any, ExistIn, Equal


class Layout(validation.BaseGroupAndDatasetValidation):
    """Layout validation main interface class to user"""

    def __init__(self):
        super().__init__(None, None)
        self._validation_results = []

    def __repr__(self):
        if self.total:
            return f'Layout(passed={self.success_ratio * 100:.1f}%)'
        return f'Layout()'

    def __getitem__(self, item: typing.Union[str, Validator]) -> validation.Validation:
        return self.specify_group(item)

    @property
    def validation_results(self) -> typing.List[validation.ValidationResult]:
        """Return list of alls validation results"""
        return self._validation_results

    def get_explanation(self, target: str, success: bool) -> str:
        raise NotImplementedError('Layout does not have an explanation')

    def print_validation_results(self, fails: bool = True, successes=True) -> None:
        """Print human-readable validation results."""
        for vr in self._validation_results:
            print(vr)

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

    @property
    def is_validated(self) -> bool:
        """True if the validation has been performed"""
        return self.fails == 0

    @property
    def fails(self) -> int:
        """Number of failed validations"""
        return sum(1 - int(r.result) for r in self.validation_results)

    @property
    def total(self) -> int:
        """Total number of performed validations"""
        return len(self.validation_results)

    @property
    def specifications(self) -> typing.List[validation.Validation]:
        """Number of specified validations"""

        def _count(subsequent_validations: typing.List, validations):
            if subsequent_validations is None:
                return validations
            if not isinstance(subsequent_validations, (list, tuple)):
                subsequent_validations = [subsequent_validations, ]
            for child in subsequent_validations:
                validations.append(child)
                if hasattr(child, 'subsequent_validations'):
                    validations = _count(child.subsequent_validations, validations)
                if hasattr(child, 'child'):
                    validations = _count(child.child, validations)
            return validations

        return _count(self.subsequent_validations, [])

    @property
    def called_validations(self) -> typing.List[validation.Validation]:
        """Return the list of called validations"""

        def _count(subsequent_validations: typing.List, _called_validations):
            if subsequent_validations is None:
                return _called_validations
            if not isinstance(subsequent_validations, (list, tuple)):
                subsequent_validations = [subsequent_validations, ]
            for child in subsequent_validations:
                if child.called:
                    _called_validations.append(child)
                if hasattr(child, 'subsequent_validations'):
                    _called_validations = _count(child.subsequent_validations, _called_validations)
                if hasattr(child, 'child'):
                    _called_validations = _count(child.child, _called_validations)
            return _called_validations

        return _count(self.subsequent_validations, [])

    @property
    def inactive_validations(self) -> typing.List[validation.Validation]:
        """Return the list of inactive validations"""

        def _count(subsequent_validations: typing.List, _called_validations):
            if subsequent_validations is None:
                return _called_validations
            if not isinstance(subsequent_validations, (list, tuple)):
                subsequent_validations = [subsequent_validations, ]
            for child in subsequent_validations:
                if not child.called:
                    _called_validations.append(child)
                if hasattr(child, 'subsequent_validations'):
                    _called_validations = _count(child.subsequent_validations, _called_validations)
                if hasattr(child, 'child'):
                    _called_validations = _count(child.child, _called_validations)
            return _called_validations

        return _count(self.subsequent_validations, [])

    @property
    def attrs(self) -> validation.AttributeValidationManager:
        """Attribute validation manager for this group or dataset"""
        return validation.AttributeValidationManager(self)

    def specify_group(self, name: typing.Union[str, Validator, None] = None) -> validation.GroupValidation:
        """Add a group validation object"""
        if isinstance(name, str):
            name = ExistIn(name)
        elif isinstance(name, Equal):
            warnings.warn('Cannot use Equal validator for group validation. Changing to '
                          'validator "ExistIn"', UserWarning)
            name = ExistIn(name.reference)
        elif name is None:
            name = Any()
        gv = validation.GroupValidation(name, self)
        return self.add_subsequent_validation(gv)

    def specify_dataset(self, name, opt: bool = None, **properties) -> validation.DatasetValidation:
        return self.specify_group(name='/').specify_dataset(name, opt, **properties)

    def validate(self, target: h5py.Group) -> typing.List[validation.ValidationResult]:
        """Validate the file using this layout specification"""

        # first reset all validators:
        for v in self.specifications:
            v.reset()

        if not isinstance(target, h5py.Group):
            with h5py.File(target) as f:
                return self.validate(f)

        assert target.name == '/'
        self._validation_results = []
        for child in self.subsequent_validations:
            if isinstance(child, validation.AttributeValidation):
                self._validation_results = child.validate(target, self._validation_results)
            elif isinstance(child, validation.GroupValidation):
                self._validation_results = child.validate(target, self._validation_results)
            elif isinstance(child, validation.DatasetValidation):
                self._validation_results = child.validate(target, self._validation_results)
            else:
                raise TypeError(f'Unknown child type: {type(child)}')

        assert len(self.specifications) == len(self.called_validations) + len(self.inactive_validations)

        # for now, every validator was executed without counting the number of fails/successes
        # A validator however can have a count requirement. We need to check for those that have (count!=None)
        # if this requirement is met.
        # therefore run over all validation_results and make a list of all validators that have a count requirement
        validation_results_with_count = {}
        for vr in self.validation_results:
            if isinstance(vr.validation, validation.AttributeValidation):
                if vr.validation.count:
                    if vr.validation not in validation_results_with_count:
                        validation_results_with_count[vr.validation] = []
                    validation_results_with_count[vr.validation].append(vr)
            # else:
            #     if vr.validation.count:
            #         if vr.validation.validator not in validation_results_with_count:
            #             validation_results_with_count[vr.validation.validator] = []
            #         validation_results_with_count[vr.validation.validator].append(vr)

        for k, v in validation_results_with_count.items():
            expected_counts = k.count
            actual_counts = sum([vr.succeeded for vr in v])
            # remove the failed validation results from the list
            self._validation_results = [vr for vr in self._validation_results if vr not in v]
            if expected_counts != actual_counts:
                # add as many as are missing (or it may be too many matches!!!):
                for i in range(abs(expected_counts - actual_counts)):
                    _v = copy.deepcopy(v[0])
                    _v.result = False
                    _v.message = f'Expected {expected_counts} matche(s), but found {actual_counts} for {_v.validation}'
                    self._validation_results.append(_v)
        return self._validation_results

    def report(self):
        """Print a report of the validation results"""
        print('Layout Validation report')
        print('------------------------')
        print(f'Number of validations (called/specified): {len(self.called_validations)}/'
              f'{len(self.specifications)}')
        print(f'Number of inactive validations: {len(self.inactive_validations)}')
        print(f'Success rate: {self.success_ratio * 100:.1f}% (n_fails={self.fails})')

    def get_failed_validations(self) -> typing.List[validation.ValidationResult]:
        """Get failed validations"""
        return [r for r in self.validation_results if r.failed]

    def get_succeeded_validations(self) -> typing.List[validation.ValidationResult]:
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

    def dumps(self, indent: int = 0, prefix='\n'):
        """Prints the validation specification to the console"""
        print(prefix)
        for child in self.subsequent_validations:
            child.dumps(indent)
