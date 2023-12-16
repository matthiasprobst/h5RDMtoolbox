import h5py
import numpy as np
import types
import uuid
from typing import Callable, Dict

import h5rdmtoolbox
from h5rdmtoolbox.database import hdfdb

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
        self.validation_rate = None

    def __repr__(self):
        if self.comment:
            return f'{self.__class__.__name__} (comment="{self.comment}", kwargs={self.kwargs})'
        return f'{self.__class__.__name__} (kwargs={self.kwargs})'

    def __call__(self, target: h5py.Group):
        if isinstance(target, h5rdmtoolbox.database.lazy.LHDFObject):
            with target as _target:
                return self.__call__(_target)

        logger.debug(f'calling {self.id}')

        res = self.func(target, **self.kwargs)
        if self.n is not None and not isinstance(res, (types.GeneratorType, tuple, list)):
            raise ValueError('"n" is specified but the return value is neither a generator nor a list or a tuple')

        if res is None:
            self.failed = True
            logger.error(f'Applying spec. "{self.id}" ("{self.comment}") on "{target}" failed.')

        if not isinstance(res, (types.GeneratorType, tuple, list)):
            # single result
            if res is None:
                self.validation_rate = 0
                self.failed = True
            else:
                self.validation_rate = 1
                self.failed = False

            if self.validation_rate > 0:
                for sub_spec in self.specifications:
                    sub_spec(res)
            return

        n_res = 0
        i_succeeded = 0
        for r in res:
            n_res += 1
            failed = r is None
            if failed:
                logger.error(f'failed: {self.id}')
            else:
                i_succeeded += 1
                for sub_spec in self.specifications:
                    sub_spec(r)

        # if n_res > 0:
        #     self.validation_rate = i_succeeded / n_res
        # else:
        #     self.validation_rate = 0
        #
        # if self.validation_rate == 0:
        #     if self.comment:
        #         logger.error(f'Applying spec. "{self.id}" ("{self.comment}") on "{target}" failed.')
        #     else:
        #         logger.error(f'Applying spec. "{self.id}" on "{target}" failed.')

        # if self.validation_rate > 0:
        #     if self.n is not None:
        #         self.failed = i_succeeded != self.n
        #         if failed:
        #             logger.error(f'spec {self.id} failed')
        #         else:
        #             logger.debug(f'spec {self.id} succeeded')

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
        >>> lay = LayoutSpecification()
        >>> spec1 = lay.add(hdfdb.H5ObjDB.find, {'$name': '/u'}, n=1)
        >>> spec2 = lay.add(...) # add another spec to layout
        >>> spec_sub1 = spec1.add(...)  # add spec to spec1 if it succeeds
        """
        new_spec = LayoutSpecification(func=func,
                                       kwargs=kwargs,
                                       n=n,
                                       comment=comment,
                                       parent=self)
        self.specifications.append(new_spec)
        return new_spec

    def print_summary(self, indent=2):
        print(' ' * indent, '>', f'"{self.comment}"' if self.comment else '"missing comment"',
              self.failed, self.validation_rate, self.kwargs, self.id, )
        indent += 2
        for spec in self.specifications:
            spec.print_summary(indent=indent)


class RootLayoutSpecification(LayoutSpecification):
    def __init__(self):
        self.specifications = []

    def __call__(self, target: h5py.Group):
        for spec in self.specifications:
            spec(target)

    def get_failed_spec(self):
        failed = []
        if self.validation_rate == 0:
            failed.append(self)
        for spec in self.specifications:
            failed.extend(spec.get_failed_spec())
        return failed

    def print_summary(self, indent=2):
        for spec in self.specifications:
            spec.print_summary(indent=indent)


# class LayoutSpecification(Layout)

def create_layout():
    return RootLayoutSpecification()
    # return Layout(hdfdb.FileDB.find_one, kwargs={'flt': {'$name': '/'}})


if __name__ == '__main__':
    lay = create_layout()

    # spec1 = lay.add(hdfdb.FileDB.find_one, flt={'$name': '/u'}, comment='/u exists')
    #
    # spec2 = lay.add(hdfdb.FileDB.find_one, flt={'$name': '/v'}, comment='/v exists')

    # spec3 = lay.add(hdfdb.FileDB.find, flt={'$name': {'$regex': '.*'},
    #                                         '$dtype': np.dtype('<f4')},
    #                 objfilter='dataset',
    #                 comment='every dataset is float32')

    spec_all_ds = lay.add(hdfdb.FileDB.find,
                          comment='Any dataset',
                          n=None,
                          flt={'$shape': {'$exists': True}},
                          objfilter='dataset')  # all datasets
    spec_all_ds_are_float32 = spec_all_ds.add(hdfdb.FileDB.find_one,
                                              comment='Is float32',
                                              flt={'$dtype': np.dtype(
                                                  '<f4')})  # applies all these on spec_all_ds results
    #
    # spec_has_units = spec_all_ds.add(hdfdb.FileDB.find, flt={'units': 'm/s'},
    #                                  comment='every dataset must have a unit attribute')  # all datasets must have units

    # assert spec_all_ds.id == spec_has_units.parent.id

    with h5py.File('test.hdf', 'w') as h5:
        ds = h5.create_dataset('u', shape=(3, 4), dtype='float32')
        ds.attrs['units'] = 'm/s'
        h5.create_dataset('v', shape=(3, 4), dtype='float64')

        res = lay(h5)

    print('--- summary ---')
    lay.print_summary()
    # for r in lay.get_failed_spec():
    #     print(r.id, r.kwargs, r.comment)
