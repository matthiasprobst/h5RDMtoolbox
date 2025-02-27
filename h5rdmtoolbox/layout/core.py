"""Layout validation module"""
import enum
import logging
import pathlib
import types
import uuid
import warnings
from typing import Dict, Union, List, Protocol, Optional, Callable, Tuple

import h5py

import h5rdmtoolbox as h5tbx

logger = logging.getLogger('h5rdmtoolbox')


class VALIDATION_FLAGS(enum.Enum):
    """Validation flags used in layout validation"""
    UNCALLED = 0
    SUCCESSFUL = 1
    FAILED = 2
    ALTERNATIVE_CALLED = 4  # an alternative spec succeeded
    INVALID_NUMBER = 8
    OPTIONAL = 16  # if a spec is optional, it is successful independent of the number of results


def _get_flag_explanations(flag):
    explanations = []
    for i in VALIDATION_FLAGS:
        if flag & i.value:
            explanations.append(i.name)
    return ', '.join(explanations)


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

    def __call__(self, *args, **kwargs) -> List: ...


def is_single_result(res) -> bool:
    """Return True if the result is a single result. This is the case if the result is not an iterable object."""
    if res is None:
        return False
    return not isinstance(res, (types.GeneratorType, tuple, list))


class SpecificationResult:
    """Stores the result of a specification call"""

    def __init__(self, target):
        self.target = target
        self.target_name = target if isinstance(target, str) else target.name
        self.target_type = 'Dataset' if isinstance(target, h5py.Dataset) else 'Group'
        self.validation_flag = VALIDATION_FLAGS.UNCALLED.value
        self.res = []

    @property
    def n_res(self) -> int:
        """Number of found objects (results)"""
        return len(self.res)


class LayoutSpecification:
    """Specification for a layout

    Parameters
    ----------
    func: QueryCallable
        Callable query according to protocol class QueryCallable to be called on the hdf5 file.
        The first argument of the function will be an opened h5py.File or h5py.Group or h5py.Dataset object.
    kwargs: Dict
        Keyword arguments passed to the func.
    n: Union[int, None, Dict]
        Number of matches or condition. Only applicable if query function (`func`) returns an iterable
        object. None means that the number can be zero as well, which makes the specification optional.
        Example: n=1 means that the specification is successful if the query function returns exactly one.
        If n is a dictionary, the key must be a comparison operator (e.g. '$eq', '$gt', '$lt', '$gte', '$lte'),
        e.g. {'$eq': 1} means that the query function must return exactly one result.
        {'$gt': 1} means that the query function must return more than one result.
    description: Optional[str]
        Optional description explaining the specification
    parent: Optional[LayoutSpecification]
        Parent specification. If the specification is a conditional one, it has a parent.
        If this is the case, the function `func` is called on the parent's results.
        If the parent's specification fails, the specification is not applied.
        If `parent` is None, the specification has no parent and is applied to the
        hdf5 root group.
    """

    def __init__(self,
                 func: QueryCallable,
                 kwargs: Dict,
                 n: Union[int, None, Dict],
                 rebase: bool = False,
                 description: Optional[str] = None,
                 parent: Optional["LayoutSpecification"] = None):
        self.func = func
        self.kwargs = kwargs
        self.rebase = rebase

        self.n, self.number_of_result_comparison = self._parse_n_def(n)

        self.id = uuid.uuid4()
        self.specifications: List[LayoutSpecification] = []
        self.alt_specifications: List[LayoutSpecification] = []
        self.parent: Optional["LayoutSpecification"] = parent
        self.description: str = description or ''
        self.results: List[Optional[SpecificationResult]] = []
        self._n_calls = 0
        self._n_fails = 0

    @property
    def validation_flag(self) -> int:
        raise NotImplementedError('validation_flag is moved')

    def __eq__(self, other) -> bool:
        """A specification is equal to another if the ID is identical or the
        function, kwargs, description and parent are identical."""
        if not isinstance(other, LayoutSpecification):
            return False
        if isinstance(other, Layout):
            return False
        same_id = self.id == other.id
        if same_id:
            return True
        same_parent = self.parent == other.parent
        same_comment = self.description == other.description
        same_kwargs = self.kwargs == other.kwargs
        same_func = self.func == other.func
        same_n = self.n == other.n

        return all([same_parent, same_comment, same_kwargs, same_func, same_n])

    @property
    def failed(self) -> bool:
        """Return True if the specification failed"""
        return any(
            r.validation_flag & VALIDATION_FLAGS.FAILED.value == VALIDATION_FLAGS.FAILED.value for r in self.results)

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
        self._n_calls = 0
        self._n_fails = 0
        self.results = []
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

    @staticmethod
    def _parse_n_def(n: int) -> Tuple[Union[int, None], Callable]:
        """Parse the number of expected results"""
        if n is None:
            return None, lambda x, y: True
            # number_of_result_comparison = lambda x, y: True
            # n = None
        else:
            if isinstance(n, int):
                if n < 1:
                    raise ValueError('n must be greater than 0')
                n = {'$eq': n}

            if not isinstance(n, dict):
                raise TypeError(f'n must be an integer or dictionary, but got {type(n)}')

            from ..database.hdfdb import query

            assert len(n) == 1, 'n must be a dictionary with exactly one key'
            for k, v in n.items():
                try:
                    number_of_result_comparison = query.operator[k]
                except KeyError:
                    raise KeyError(f'Unexpected operator. Valid ones are: {list(query.operator.keys())}')
                assert isinstance(v, int), 'n must be an integer'
                n = v
        return n, number_of_result_comparison

    def __repr__(self):
        _kwargs = _replace_callables_with_names(self.kwargs)
        if self.description:
            return f'{self.__class__.__name__}(description="{self.description}", kwargs={_kwargs})'
        return f'{self.__class__.__name__}(kwargs={_kwargs})'

    def __call__(self, target: Union[h5py.Group, h5py.Dataset]):
        if isinstance(target, h5tbx.database.lazy.LHDFObject):
            with target as _target:
                return self.__call__(_target)

        if self.rebase and isinstance(target, (h5tbx.Dataset, h5tbx.Group)):
            target = target.rootparent

        self._n_calls += 1
        scr = SpecificationResult(target)

        if self.n is None:
            # per definition successful since n is None
            scr.validation_flag = VALIDATION_FLAGS.SUCCESSFUL.value + VALIDATION_FLAGS.OPTIONAL.value

        logger.debug(f'Calling spec {self} on hdf obj {target}.')
        res = self.func(target, **self.kwargs)
        if res is None:
            res = []
        elif is_single_result(res):
            res = [res]
            if self.n is None:
                self.n, self.number_of_result_comparison = self._parse_n_def(1)

        if not is_single_result(res) and res is not None:
            res = list(res)

        # assign result to scr
        scr.res = res

        if not res:
            # first assume failure unless n=None. There might be an alternative spec registered though.
            # The following will update `res`
            if self.n is None:  # query is optional!
                scr.validation_flag = VALIDATION_FLAGS.SUCCESSFUL.value + VALIDATION_FLAGS.OPTIONAL.value
            else:
                scr.validation_flag = VALIDATION_FLAGS.FAILED.value

            # If alternative specifications exist, try them. This will only be performed if self.n is not None
            if len(self.alt_specifications) > 0 and self.n is not None:
                alt_spec_successes = []
                res = []
                for alt_spec in self.alt_specifications:
                    alt_res = alt_spec.func(target, **alt_spec.kwargs)

                    alt_sr = SpecificationResult(target)
                    alt_sr.res = alt_res

                    if not is_single_result(alt_res):
                        alt_res = list(alt_res)

                    if alt_res:
                        alt_sr.validation_flag = VALIDATION_FLAGS.SUCCESSFUL.value
                        alt_spec_successes.append(True)
                    else:
                        alt_sr.validation_flag = VALIDATION_FLAGS.FAILED.value
                        alt_spec_successes.append(False)

                    res.extend(alt_res)
                    scr.res.extend(alt_res)

                # failed = not any(alt_spec_successes)
                if any(alt_spec_successes):
                    logger.debug('An alternative succeeded!')
                    if scr.validation_flag & VALIDATION_FLAGS.FAILED.value:
                        scr.validation_flag -= VALIDATION_FLAGS.FAILED.value
                    scr.validation_flag += VALIDATION_FLAGS.ALTERNATIVE_CALLED.value
                else:
                    self._n_fails += 1
                    logger.error(f'Applying spec. "{self}" on "{target}" failed.')
                    scr.validation_flag = VALIDATION_FLAGS.FAILED.value + VALIDATION_FLAGS.ALTERNATIVE_CALLED.value

        # now, for successful results, let's apply the sub-specifications if exist
        # and check how many results we have and if the number of results is correct (if n is specified)
        if is_single_result(res):
            # as there is a result, the specification is successful as n=1 is implicit
            scr.validation_flag = VALIDATION_FLAGS.SUCCESSFUL.value

            # check sub-specifications
            for sub_spec in self.specifications:
                sub_spec(res)

            self.results.append(scr)
            return

        n_res = len(res)
        if res:  # if no alternative was defined, res may still be None!
            # continue here if res is an iterable object
            for r in res:
                if not r:  # first result failed
                    logger.error(f'Applying spec. "{self}" on "{target}" failed.')
                    self._n_fails += 1
                else:
                    # if it was successful, we can check the sub-specifications
                    for sub_spec in self.specifications:
                        logger.debug(f'Calling spec {sub_spec} to hdf obj {r}.')
                        sub_spec(r)

        # logger.debug(f'Validation {self} found {n_res} results from which {self._n_fails} failed.')
        # If the number of successful results is not specified, it means, that
        # the spec is optional. so it is successful in any case!
        if self.n is not None:
            if self.number_of_result_comparison(n_res, self.n):
                scr.validation_flag = VALIDATION_FLAGS.SUCCESSFUL.value
            else:  # if self.n != n_res:
                self._n_fails += 1
                scr.validation_flag = VALIDATION_FLAGS.FAILED.value + VALIDATION_FLAGS.INVALID_NUMBER.value
                logger.error(f'Applying spec. "{self}" failed due to not '
                             f'matching the number of results: {self.n} != {n_res}')
        self.results.append(scr)

    def add(self,
            func: QueryCallable,
            *,
            n: Optional[Union[int, None, Dict]] = None,
            rebase: bool = False,
            description: Optional[str] = None,
            **kwargs):
        """
        Add a specification by providing a callable query obj. Optionally, the
        number of exact matches can be provided as well as the a description string.
        The kwargs are passed to the callable

        Parameters
        ----------
        func: Callable
            Function to be called on the hdf5 file
        n: int
            Number of matches or query dictionary. None indicates optional specification.
        description: Optional[str]
            Optional description explaining the specification
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
                                       rebase=rebase,
                                       description=description,
                                       parent=self)
        for spec in self.specifications:
            if spec == new_spec:
                warnings.warn(f'Specification "{new_spec}" already exists. Skipping.',
                              UserWarning)
                return spec
        self.specifications.append(new_spec)
        return new_spec

    def add_alternative(self,
                        func: QueryCallable,
                        *,
                        n: Union[int, None, Dict],
                        description: Optional[str] = None,
                        **kwargs):
        """Add an alternative specification by providing a callable query obj. Optionally, the
        number of exact matches can be provided as well as the a description string.
        The kwargs are passed to the callable
        Either the parent or the alternative specification must be successful.

        .. note::

            An alternative query can only added to specifications which have a number of expected results (n!=None).

        Parameters
        ----------
        func: Callable
            Function to be called on the hdf5 file
        n: Union[int, None, Dict]
            Number of matches or query dictionary. None indicates optional specification.
        description: Optional[str]
            Optional description explaining the specification
        kwargs: Dict
            Keyword arguments passed to the func

        """
        if self.n is None:
            raise ValueError('Parent specification must not be an optional specification. Please provide a number of '
                             'expected results.')
        new_spec = LayoutSpecification(func=func,
                                       kwargs=kwargs,
                                       n=n,
                                       description=description,
                                       parent=self)
        for spec in self.alt_specifications:
            if spec == new_spec:
                warnings.warn(f'Specification "{new_spec}" already exists. Skipping.',
                              UserWarning)
                return spec
        self.alt_specifications.append(new_spec)
        return new_spec

    def is_valid(self):
        """Return True if the specification is valid"""
        if self.n_calls == 0:
            print(f'{self} has not been called yet')
            return False
        if self.n is None:
            return True
        if self.failed:
            print(f'{self} failed')
            return False
        return all(spec.is_valid() for spec in self.specifications)

    def get_valid(self) -> List['LayoutSpecification']:
        """Return all successful specifications"""
        if self.n_calls == 0:
            return []  # has not been called yet, thus cannot be valid

        valid: List[LayoutSpecification] = []

        if not self.failed and self.n_calls > 0 and not self.failed:
            valid.append(self)

        if self.specifications:
            for spec in self.specifications:
                valid.extend(spec.get_valid())
        return valid

    def get_failed(self) -> List['LayoutSpecification']:
        """Return a list of failed specifications"""
        if self.failed is True:
            return [self]
        failed = []
        if self.failed:
            failed.append(self)
        if self.specifications:
            failed.extend(spec.get_failed() for spec in self.specifications)
            # flatten list:
            return [item for sublist in failed for item in sublist]
        return failed

    def get_summary(self, exclude_keys: Optional[Union[str, List[str]]] = None) -> List[Dict]:
        """return a summary as dictionary"""
        if isinstance(exclude_keys, str):
            exclude_keys = [exclude_keys, ]
        data = []
        for res in self.results:
            data.append({'id': self.id,
                         'called': len(self.results) > 0,
                         # 'n_calls/n_res/n_fails': f'{self.n_calls}/{n_res}/{self.n_fails}' if self.called else '-(-)',
                         'flag': res.validation_flag,
                         'flag description': _get_flag_explanations(res.validation_flag),
                         'description': self.description,
                         'target_type': res.target_type,
                         'target_name': res.target_name,
                         # '_n_fails': self._n_fails,
                         'func': f'{self.func.__module__}.{self.func.__name__}',
                         'kwargs': self.kwargs,
                         })

        if exclude_keys is None:
            exclude_keys = []
        elif isinstance(exclude_keys, str):
            exclude_keys = [exclude_keys, ]

        for key in exclude_keys:
            # pop keys from dict:
            for i, d in enumerate(data):
                data[i].pop(key)

        for spec in self.specifications:
            data.extend(spec.get_summary(exclude_keys))
        return data


class LayoutResult:
    """Container for the result of a layout validation. It only contains a list of failed specs."""

    def __init__(self, specifications: List[LayoutSpecification]):
        self.specifications: List[LayoutSpecification] = specifications

    def get_failed(self) -> List[LayoutSpecification]:
        """Return a list of failed specifications"""
        failed = [spec.get_failed() for spec in self.specifications]
        # flatten list:
        return [item for sublist in failed for item in sublist]

    def get_valid(self) -> List[LayoutSpecification]:
        """Return a list of valid specifications"""
        valid_specs = [spec.get_valid() for spec in self.specifications]
        # flatten list:
        return [item for sublist in valid_specs for item in sublist]

    def is_valid(self) -> bool:
        """Return True if the layout is valid, which is the case if no specs failed"""
        return len(self.get_failed()) == 0

    def get_summary(self, exclude_keys: Optional[Union[str, List[str]]] = None,
                    failed_only: bool = False) -> List[Dict]:
        """return a list of dictionaries containing information about a specification call"""
        data = []
        for spec in self.specifications:
            s = spec.get_summary(exclude_keys=exclude_keys)
            if failed_only:
                data.extend([d for d in s if d['flag'] & 2 == 2])
            else:
                data.extend(s)
        return data

    def print_summary(self, exclude_keys: Optional[Union[str, List[str]]] = None,
                      failed_only: bool = False):
        """Prints a summary of the specification. Requires the tabulate package."""
        try:
            from tabulate import tabulate
        except ImportError:
            raise ImportError('Please install tabulate to use this method')
        print('\nSummary of layout validation')
        print(tabulate(self.get_summary(exclude_keys, failed_only), headers='keys', tablefmt='psql'))
        if self.is_valid():
            print('--> Layout is valid')
        else:
            print('--> Layout validation found issues!')


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

    def __init__(self, description: str = ''):
        self.description = description  # description of the layout class
        self.specifications: List[LayoutSpecification] = []

    def __repr__(self):
        return f'{self.__class__.__name__} (description="{self.description}")'

    def __eq__(self, other):
        if not isinstance(other, Layout):
            return False
        return self.specifications == other.specifications

    def validate(self, filename_or_root_group: Union[str, pathlib.Path, h5py.Group]) -> LayoutResult:
        """Validate the layout by passing a filename or an opened root group"""
        self.reset()

        # if isinstance(filename_or_root_group, (str, pathlib.Path)):
        #     with h5tbx.File(filename_or_root_group, mode='r') as h5:
        #         return self.validate(h5)

        # if isinstance(filename_or_root_group, h5py.Group):
        #     if not filename_or_root_group.name == '/':
        #         raise ValueError('If passing an HDF5 group, a root group must be passed')

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
