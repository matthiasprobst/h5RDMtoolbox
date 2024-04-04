import h5py
import logging
import pathlib
import types
import uuid
import warnings
from typing import Dict, Union, List, Protocol, Optional

import h5rdmtoolbox as h5tbx

logger = logging.getLogger('h5rdmtoolbox')


def _replace_callables_with_names(dict_with_callables: Dict) -> Dict:
    """Replace all callables in a dictionary with their names plus '()'
    Used by __repr__ of LayoutSpecification"""
    dict_with_callables = dict_with_callables.copy()
    for key in dict_with_callables.keys():
        if callable(dict_with_callables[key]):
            dict_with_callables[key] = f'{dict_with_callables[key].__name__}()'
        elif isinstance(dict_with_callables[key], dict):
            _replace_callables_with_names(dict_with_callables[key])
    return dict_with_callables


class QueryCallable(Protocol):
    """Protocol class for classes passed to the LayoutSpecification class.

    Those classes must implement the method find()
    """

    def find(self, target: Union[str, pathlib.Path, h5tbx.Group], **kwargs): ...


class LayoutSpecification:
    """Specification for a layout

    Parameters
    ----------
    func: QueryCallable
        Callable query according to protocol class QueryCallable to be called on the hdf5 file.
        The first argument of the function will be an opened h5py.File or h5py.Group or h5py.Dataset object.
    kwargs: Dict
        Keyword arguments passed to the func.
    n: int
        Number of matches if function returns an iterable object. Only used, if `func`
        return an iterable object.
    comment: Optional[str]
        Optional comment explaining the specification
    parent: Optional[LayoutSpecification]
        Parent specification. If the specification is a conditional one, it has a parent.
        If this is the case, the function `func` is called on the parent's results.
        If the parent's specification fails, the specification is not applied.
        If `parent` is None, the specification has no parent and is applied to the
        hdf5 root group.
    """

    def __init__(self,
                 func: QueryCallable,
                 kwargs,
                 n=None,
                 comment: str = None,
                 parent=None):
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

    def __eq__(self, other) -> bool:
        """A specification is equal to another if the ID is identical or the
        function, kwargs, comment and parent are identical."""
        if not isinstance(other, LayoutSpecification):
            return False
        if isinstance(other, Layout):
            return False
        same_id = self.id == other.id
        if same_id:
            return True
        same_parent = self.parent == other.parent
        same_comment = self.comment == other.comment
        same_kwargs = self.kwargs == other.kwargs
        same_func = self.func == other.func
        same_n = self.n == other.n

        return all([same_parent, same_comment, same_kwargs, same_func, same_n])

    @property
    def n_calls(self) -> int:
        """Return number of calls"""
        return self._n_calls

    @property
    def n_fails(self) -> int:
        """Return number of failed calls"""
        return self._n_fails

    def reset(self) -> None:
        """Reset the specification and all its children"""
        self.failed = None
        self._n_calls = 0
        self._n_fails = 0
        for spec in self.specifications:
            spec.reset()

    @property
    def called(self) -> bool:
        """Return True if the specification has been called at least once.
        This is determined by the number of calls."""
        return self.n_calls > 0

    @property
    def n_successes(self):
        """Return number of successful calls"""
        if self.n_calls == 0:
            raise ValueError('Not called')
        return self.n_calls - self._n_fails

    def __repr__(self):
        _kwargs = _replace_callables_with_names(self.kwargs)
        if self.comment:
            return f'{self.__class__.__name__} (comment="{self.comment}", kwargs={_kwargs})'
        return f'{self.__class__.__name__} (kwargs={_kwargs})'

    def __call__(self, target: Union[h5py.Group, h5py.Dataset]):
        if isinstance(target, h5tbx.database.lazy.LHDFObject):
            with target as _target:
                return self.__call__(_target)

        self._n_calls += 1
        logger.debug(f'calling spec (id={self.id}) with func={self.func.__module__}.{self.func.__name__} and '
                     f'kwargs {self.kwargs}')

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
                    logger.debug(f'Calling spec {sub_spec} to hdf obj {r}.')
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

    def add(self,
            func: QueryCallable,
            *,
            n: Optional[int] = None,
            comment: Optional[str] = None,
            **kwargs):
        """
        Add a specification by providing a callable query obj. Optionally, the
        number of exact matches can be provided as well as the a comment string.
        The kwargs are passed to the callable

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
        >>> from h5rdmtoolbox.database import FileDB
        >>> lay = LayoutSpecification()
        >>> spec1 = lay.__set_meta_field__(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        >>> spec2 = lay.__set_meta_field__(...) # add another spec to layout
        >>> spec_sub1 = spec1.__set_meta_field__(...)  # add spec to `spec1` if it succeeds and apply to all results of `spec1`
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

    def get_valid(self) -> List['LayoutSpecification']:
        """Return all successful specifications"""
        if self.failed is False:
            return [self]
        valid = []
        if self.n_calls > 0 and self.failed is False:
            valid.append(self)
        if self.specifications:
            valid.extend(spec.get_valid() for spec in self.specifications)
            # flatten list:
            return [item for sublist in valid for item in sublist]
        return valid

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

    def get_summary(self) -> List[Dict]:
        """return a summary as dictionary"""
        if len(self.specifications) == 0:
            return [{'id': self.id,
                     'failed': self.failed,
                     'n_calls': self.n_calls,
                     # '_n_fails': self._n_fails,
                     'func': f'{self.func.__module__}.{self.func.__name__}',
                     'kwargs': self.kwargs,
                     'comment': self.comment,
                     }]
        data = []
        for spec in self.specifications:
            data.extend(spec.get_summary())
        return data


class LayoutResult:
    """Container for the result of a layout validation. It only contains a list of failed specs."""

    def __init__(self, specifications: List[LayoutSpecification]):
        self.specifications: List[LayoutSpecification] = specifications

    def __len__(self):
        return len(self.specifications)

    def get_failed(self) -> List[LayoutSpecification]:
        """Return a list of failed specifications"""
        failed = [spec.get_failed() for spec in self.specifications]
        # flatten list:
        return [item for sublist in failed for item in sublist]

    def get_valid(self) -> List[LayoutSpecification]:
        """Return a list of failed specifications"""
        failed = [spec.get_valid() for spec in self.specifications]
        # flatten list:
        return [item for sublist in failed for item in sublist]

    def is_valid(self) -> bool:
        """Return True if the layout is valid, which is the case if no specs failed"""
        return len(self.get_valid()) == 0

    def get_summary(self) -> Dict:
        """return a summary as dictionary"""
        data = []
        for spec in self.specifications:
            data.extend(spec.get_summary())
        return data

    def print_summary(self):
        """Prints a summary of the specification. Requires the tabulate package."""
        try:
            from tabulate import tabulate
        except ImportError:
            raise ImportError('Please install tabulate to use this method')
        print('\nSummary of layout validation')
        print(tabulate(self.get_summary(), headers='keys', tablefmt='psql'))


class Layout(LayoutSpecification):
    """A layout is a collection of specifications that can be applied to an HDF5 file or group.

    The class is inherited from LayoutSpecification. Some methods are overwritten.

    Examples
    --------
    >>> from h5rdmtoolbox import layout
    >>> lay = layout.Layout()
    >>> spec_all_dataset = lay.__set_meta_field__(
    >>> hdfdb.FileDB.find,  # query function
    >>>     flt={},
    >>>     objfilter='dataset'
    >>> )
    >>>
    >>> # all datasets must be compressed with gzip (conditional spec. only called if parent spec is successful)
    >>> spec_compression = spec_all_dataset.__set_meta_field__(
    >>>     hdfdb.FileDB.find_one,  # query function
    >>>     flt={'$compression': 'gzip'}  # query parameter
    >>> )
    >>>
    >>> # the file must have the dataset "/u"
    >>> spec_ds_u = lay.__set_meta_field__(
    >>>     hdfdb.FileDB.find,  # query function
    >>>     flt={'$name': '/u'},
    >>>     objfilter='dataset'
    >>> )
    >>> lay.validate('path/to/file.h5')
    """

    def __init__(self):
        self.specifications: List[LayoutSpecification] = []

    def __eq__(self, other):
        if not isinstance(other, Layout):
            return False
        return self.specifications == other.specifications

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

        return LayoutResult(self.specifications)

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
