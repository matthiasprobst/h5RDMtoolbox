import h5py
import pathlib
import types
import uuid
import warnings
from typing import Callable, Dict, Union, List

import h5rdmtoolbox

logger = h5rdmtoolbox.utils.create_tbx_logger('layout')


class LayoutSpecification:

    def __init__(self, func, kwargs, n=None, comment: str = None, parent=None):
        self.func = func
        self.kwargs = kwargs
        self.n = n
        self.id = uuid.uuid4()
        self.specifications = []
        self.parent = parent
        self.comment = comment
        self.failed = None
        self._n_calls = 0
        self._n_fails = 0

    def __eq__(self, other):
        if not isinstance(other, LayoutSpecification):
            return False
        same_id = self.id == other.id
        same_props = self.func == other.func and self.kwargs == other.kwargs
        return same_id or same_props

    @property
    def n_calls(self):
        """Return number of calls"""
        return self._n_calls

    @property
    def n_fails(self):
        """Return number of failed calls"""
        return self._n_fails

    def reset(self):
        """Reset the specification and all its children"""
        self.failed = None
        self._n_calls = 0
        self._n_fails = 0
        for spec in self.specifications:
            spec.reset()

    @property
    def called(self):
        """Return True if the specification has been called at least once"""
        return self.n_calls > 0

    @property
    def n_successes(self):
        """Return number of successful calls"""
        if self.n_calls == 0:
            raise ValueError('Not called')
        return self.n_calls - self._n_fails

    def __repr__(self):
        if self.comment:
            return f'{self.__class__.__name__} (comment="{self.comment}", kwargs={self.kwargs})'
        return f'{self.__class__.__name__} (kwargs={self.kwargs})'

    def __call__(self, target: Union[h5py.Group, h5py.Dataset]):
        if isinstance(target, h5rdmtoolbox.database.lazy.LHDFObject):
            with target as _target:
                return self.__call__(_target)

        self._n_calls += 1
        logger.debug(f'calling {self.id}')

        res = self.func(target, **self.kwargs)
        if self.n is not None and not isinstance(res, (types.GeneratorType, tuple, list)):
            raise ValueError('"n" is specified but the return value is neither a generator nor a list or a tuple')

        if res is None:
            self.failed = True
            self._n_fails += 1
            logger.error(f'Applying spec. "{self}" on "{target}" failed.')

        if not isinstance(res, (types.GeneratorType, tuple, list)):
            # single result
            if res is None:
                self.failed = True
            else:
                self.failed = False

            if not self.failed:
                for sub_spec in self.specifications:
                    sub_spec(res)
            return

        n_res = 0
        for r in res:
            n_res += 1
            failed = r is None
            if failed:
                logger.error(f'Applying spec. "{self}" on "{target}" failed.')
                self._n_fails += 1
            else:
                for sub_spec in self.specifications:
                    sub_spec(r)

        if self.n is None:
            if self.failed is None:
                self.failed = False
        if self.n is not None:
            if self.n == n_res:
                self.failed = False
            else:  # if self.n != n_res:
                self.failed = True
                logger.error(f'Applying spec. "{self}" failed due to not '
                             f'matching the number of results: {self.n} != {n_res}')

    def add(self, func: Callable, *, n: int = None, comment: str = None, **kwargs):
        """


        Parameters
        ----------
        func: Callable
            Function to be called on the hdf5 file
        n: int
            Number of matches if function returns an iterable object
        comment: Optional[str]
            Optional comment explaining the specification
        kwargs: Dict
            Keyword arguments passed to the func

        Returns
        -------
        LayoutSpecification

        Examples
        --------
        >>> from h5rdmtoolbox.database import hdfdb
        >>> lay = LayoutSpecification()
        >>> spec1 = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        >>> spec2 = lay.add(...) # add another spec to layout
        >>> spec_sub1 = spec1.add(...)  # add spec to `spec1` if it succeeds and apply to all results of `spec1`
        """
        new_spec = LayoutSpecification(func=func,
                                       kwargs=kwargs,
                                       n=n,
                                       comment=comment,
                                       parent=self)
        for spec in self.specifications:
            if spec == new_spec:
                warnings.warn(f'Specification "{new_spec}" already exists. Skipping.',
                              UserWarning)
                return spec
        self.specifications.append(new_spec)
        return new_spec

    def is_valid(self):
        """Return True if the specification is valid"""
        if self.n_calls == 0:
            print(f'{self} has not been called yet')
            return False
        if self.failed is True:
            print(f'{self} failed')
            return False
        return all(spec.is_valid() for spec in self.specifications)

    def get_failed(self) -> List['LayoutSpecification']:
        """Return a list of failed specifications"""
        if self.failed is True:
            return [self]
        failed = []
        if self.n_fails > 0:
            failed.append(self)
        if self.specifications:
            failed.extend(spec.get_failed() for spec in self.specifications)
            # flatten list:
            return [item for sublist in failed for item in sublist]
        return failed

    def print_summary(self, indent=2):
        print(' ' * indent, '>', f'"{self.comment}"' if self.comment else '"missing comment"',
              ' | failed: ', self.failed, f'| n_calls={self.n_calls} | ', f'| _n_fails={self._n_fails} | ',
              self.kwargs, self.id, )
        indent += 2
        for spec in self.specifications:
            spec.print_summary(indent=indent)


class LayoutResult:

    def __init__(self, list_of_failed_specs: List[LayoutSpecification]):
        self.list_of_failed_specs = list_of_failed_specs

    def is_valid(self):
        return len(self.list_of_failed_specs) == 0


class Layout(LayoutSpecification):
    def __init__(self):
        self.specifications = []

    def validate(self, filename_or_root_group: Union[str, pathlib.Path, h5py.Group]) -> LayoutResult:
        """Validate the layout by passing a filename or an opened root group"""
        if isinstance(filename_or_root_group, h5py.Group):
            if not filename_or_root_group.name == '/':
                raise ValueError('If passing an HDF5 group, a root group must be passed')

        # first reset all specs (n_calls = 0, _n_fails = 0, failed = None)
        for spec in self.specifications:
            spec.reset()

        for spec in self.specifications:
            spec(filename_or_root_group)

        return LayoutResult(self.get_failed())

    def __call__(self, *args, **kwargs):
        raise RuntimeError('Layout cannot be called. User `.validate()` to validate')

    def is_valid(self) -> bool:
        """Return True if all specifications are valid.
        A specification is valid it is has been called and has not been failed"""
        return all(spec.is_valid() for spec in self.specifications)

    def get_failed(self) -> List[LayoutSpecification]:
        """Return a list of failed specifications"""
        failed = [spec.get_failed() for spec in self.specifications]
        # flatten list:
        return [item for sublist in failed for item in sublist]

    def print_summary(self, indent=2):
        """Print a summary of the layout"""
        for spec in self.specifications:
            spec.print_summary(indent=indent)
