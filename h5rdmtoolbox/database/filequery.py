import os
import pathlib
import re
from itertools import chain
from typing import List
from typing import Union, Dict, Callable

import h5py
import numpy as np
import pandas as pd

from ..wrapper import open_wrapper


# implementation similar to pymongo:
# https://www.mongodb.com/docs/manual/reference/operator/query/

def _eq(a, b):
    return a == b


def _gt(a, b):
    return a > b


def _gte(a, b):
    return a >= b


def _lt(a, b):
    return a < b


def _lte(a, b):
    return a <= b


def _regex(value, pattern):
    return re.search(pattern, value)


def _eq_name(node, name):
    return node.name == name


def _eq_basename(node, name):
    return node.basename == name


def _eq_ndim(node, ndim):
    return node.ndim == ndim


def _eq_shape(node, shape):
    return node.shape == shape


_operator = {'$regex': _regex, '$eq': _eq, '$gt': _gt, '$gte': _gte, '$lt': _lt, '$lte': _lte}


class RecFind:
    def __init__(self, func: Callable, attribute, value):
        self._func = func
        self._attribute = attribute
        self._value = value
        self.found_objects = []

    def __call__(self, name, h5obj):
        try:
            objattr = h5obj.__getattribute__(self._attribute)
            if self._func(objattr, self._value):
                self.found_objects.append(h5obj)
        except AttributeError:
            pass


class RecAttrFind:
    def __init__(self, func: Callable, attribute, value):
        self._func = func
        self._attribute = attribute
        self._value = value
        self.found_objects = []

    def __call__(self, name, obj):
        if self._attribute in obj.attrs:
            if self._func(obj.attrs[self._attribute], self._value):
                self.found_objects.append(obj)


class RecPropCollect:
    """Visititems class to collect all class attributes matching a certain string"""

    def __init__(self, attribute_name: str, objfilter: Union[h5py.Group, h5py.Dataset, None]):
        self._attribute_name = attribute_name
        self._objfilter = objfilter
        self.found_objects = []

    def __call__(self, name, obj):
        if self._objfilter is None:
            try:
                propval = obj.__getattribute__(self._attribute_name)
                self.found_objects.append(propval)
            except AttributeError:
                pass
        else:
            if isinstance(obj, self._objfilter):
                try:
                    propval = obj.__getattribute__(self._attribute_name)
                    self.found_objects.append(propval)
                except AttributeError:
                    pass


class RecAttrCollect:
    """Visititems class to collect all attributes matching a certain string"""

    def __init__(self, attribute_name: str, objfilter: Union[h5py.Group, h5py.Dataset, None]):
        self._attribute_name = attribute_name
        self._objfilter = objfilter
        self.found_objects = []

    def __call__(self, name, obj):
        if self._objfilter is None:
            if self._attribute_name in obj.attrs:
                self.found_objects.append(obj.attrs[self._attribute_name])
        else:
            if isinstance(obj, self._objfilter):
                if self._attribute_name in obj.attrs:
                    self.found_objects.append(obj.attrs[self._attribute_name])


def _find_in_external_link(el: h5py.ExternalLink, operator: Callable, name, value, found_objs):
    with open_wrapper(el.filename) as h5el:
        rf = RecFind(operator, name, value)
        h5el[el.path].visititems(rf)
        for found_obj in rf.found_objects:
            # add external link object:
            found_objs.append(h5py.ExternalLink(el.filename, el.path + found_obj.name[1:]))
    return


def _h5find(h5obj: Union[h5py.Group, h5py.Dataset], qk, qv, recursive):
    """

    Parameters
    ----------
    h5obj: h5py.Group, h5py.Dataset
        h5py object (group or dataset) to start search from

    Returns
    -------

    """
    found_objs = []

    is_hdf_attrs_search = qk[0] != '$'

    if not isinstance(qv, Dict):
        qv = {'$eq': qv}

    # find objects with equal value
    if is_hdf_attrs_search:
        for ok, ov in qv.items():
            if qk in h5obj.attrs:
                if _operator[ok](h5obj.attrs[qk], ov):
                    found_objs.append(h5obj)
            for hv in h5obj.values():
                if qk in hv.attrs:
                    if _operator[ok](hv.attrs[qk], ov):
                        found_objs.append(hv)
            if recursive:
                rf = RecAttrFind(_operator[ok], qk, ov)
                h5obj['/'].visititems(rf)
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
    else:
        for ok, ov in qv.items():
            # try:
            #     objattr = h5obj.__getattribute__(qk[1:])
            #     if _operator[ok](objattr, ov):
            #         found_objs.append(h5obj)
            # except AttributeError:
            #     pass
            for hk, hv in h5obj.items():
                if isinstance(hv, h5py.Dataset):
                    try:
                        objattr = hv.__getattribute__(qk[1:])
                        if _operator[ok](objattr, ov):
                            found_objs.append(hv)
                    except AttributeError:
                        pass

            if recursive:
                rf = RecFind(_operator[ok], qk[1:], ov)
                h5obj.visititems(rf)
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
    return found_objs


def find(h5obj: Union[h5py.Group, h5py.Dataset],
         flt: Dict,
         objfilter: Union[h5py.Group, h5py.Dataset, None],
         recursive: bool,
         find_one: bool):
    # start with some input checks:
    if not isinstance(flt, Dict):
        raise TypeError(f'Filter must be a dictionary not {type(flt)}')

    # actual filter:
    results = []
    for k, v in flt.items():
        _results = _h5find(h5obj, k, v, recursive)
        if find_one:
            if len(_results):
                if objfilter:
                    for r in _results:
                        if isinstance(r, objfilter):
                            return r
                return _results[0]
        results.append(_results)
    if find_one:
        return  # Nothing found

    common_results = list(set.intersection(*map(set, results)))
    if objfilter:
        return [r for r in common_results if isinstance(r, objfilter)]
    return common_results


def distinct(h5obj: Union[h5py.Group, h5py.Dataset], key: str,
             objfilter: Union[h5py.Group, h5py.Dataset, None]) -> List[str]:
    """Return a distinct list of all found targets. A target generally is
    understood to be an attribute name. However, by adding a $ in front, class
    properties can be found, too, e.g. $shape will return all distinct shapes of the
    passed group."""
    if key[0] == '$':
        rpc = RecPropCollect(key[1:], objfilter)

        h5obj.visititems(rpc)
        if objfilter:
            if isinstance(h5obj, objfilter):
                try:
                    propval = h5obj.__getattribute__(key[1:])
                    rpc.found_objects.append(propval)
                except AttributeError:
                    pass
        else:
            try:
                propval = h5obj.__getattribute__(key[1:])
                rpc.found_objects.append(propval)
            except AttributeError:
                pass

        return list(set(rpc.found_objects))

    rac = RecAttrCollect(key, objfilter)
    for k, v in h5obj.attrs.items():
        if k == key:
            rac.found_objects.append(v)
    if isinstance(h5obj, h5py.Group):
        h5obj.visititems(rac)
        if objfilter:
            if isinstance(h5obj, objfilter):
                if key in h5obj.attrs:
                    rac.found_objects.append(h5obj.attrs[key])
        else:
            if key in h5obj.attrs:
                rac.found_objects.append(h5obj.attrs[key])

    return list(set(rac.found_objects))


class DatasetValues:
    def __init__(self, arr: Dict):
        self.arr = arr

    def to_DataFrame(self, axis=0, join='outer') -> pd.DataFrame:
        """Return DataFrame. Only works for 1D data!"""
        if np.all([a[:].ndim == 1 for a in self.arr.values()]):
            keys = [os.path.dirname(k) for k in list(self.arr.keys())]
            frames = [pd.DataFrame({os.path.basename(k): v[:]}) for k, v in self.arr.items()]
            return pd.concat(frames, axis=axis, join=join, keys=keys)
        raise ValueError('to_DataFrame() only works with 1D data')


class H5Objects:

    def __init__(self, h5objdict: Dict):
        self.h5objdict = h5objdict
        # TODO: check if all are the same object type!

    @property
    def names(self) -> List[str]:
        """Names of objects"""
        return [obj for obj in self.h5objdict.keys()]

    @property
    def basenames(self) -> List[str]:
        """Names of objects"""
        return [os.path.basename(obj.name) for obj in self.h5objdict.values()]

    def __getitem__(self, item):
        if isinstance(self.h5objdict[list(self.h5objdict.keys())[0]], h5py.Dataset):
            return DatasetValues({k: v.values for k, v in self.h5objdict.items()})
        raise TypeError('Cannot slice hdf group objects')


class H5Files:
    """H5File-like interface for multiple HDF Files"""

    def __init__(self, *filenames, h5wrapper=None):
        if isinstance(filenames[0], (list, tuple)):
            if len(filenames) != 1:
                raise ValueError('Expecting filenames to be passe separately or in alist/tuple')
            self._list_of_filenames = [pathlib.Path(f) for f in filenames[0]]
        else:
            self._list_of_filenames = [pathlib.Path(f) for f in filenames]
        self._opened_files = {}
        self._h5wrapper = h5wrapper

    def __getitem__(self, item) -> Union[h5py.Group, H5Objects]:
        """If integer, returns item-th root-group. If string,
        a list of objects of that item is returned"""
        if isinstance(item, int):
            return self._opened_files[list(self.keys())[item]]
        return H5Objects({f'{key}/item': rgrp[item] for key, rgrp in zip(self.keys(), self.values()) if item in rgrp})

    def __enter__(self):
        for filename in self._list_of_filenames:
            try:
                if self._h5wrapper is None:
                    h5file = open_wrapper(filename, mode='r')
                else:
                    h5file = self._h5wrapper(filename, mode='r')
                self._opened_files[str(filename)] = h5file
            except RuntimeError as e:
                print(f'RuntimeError: {e}')
                for h5file in self._opened_files.values():
                    h5file.close()
                self._opened_files = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._opened_files = {}
        self.close()

    def find_one(self, flt: Union[Dict, str],
                 objfilter=None,
                 rec: bool = True) -> Union[h5py.Group, h5py.Dataset, None]:
        """See find() in h5file.py"""
        for v in self.values():
            found = find(v, flt, objfilter=objfilter, recursive=rec, find_one=True)
            if found:
                return found

    def find(self, flt: Union[Dict, str], objfilter=None, rec: bool = True):
        """See find() in h5file.py"""
        found = [find(v, flt, objfilter=objfilter, recursive=rec, find_one=False) for v in self.values()]
        return list(chain.from_iterable(found))

    def keys(self):
        """Return all opened filename stems"""
        return self._opened_files.keys()

    def values(self):
        """Return all group instances in the file stems"""
        return self._opened_files.values()

    def close(self):
        """Close all opened files"""
        for h5file in self._opened_files.values():
            h5file.close()
