"""filequery module"""
import h5py
import pathlib
import re
from typing import List, Union, Dict, Callable

from . import lazy
from ..utils import process_obj_filter_input


# implementation similar to pymongo:
# https://www.mongodb.com/docs/manual/reference/operator/query/

def _eq(a, b):
    """Check if a == b"""
    return a == b


def _gt(a, b):
    """Check if a > b"""
    return a > b


def _gte(a, b):
    """Check if a >= b"""
    return a >= b


def _lt(a, b):
    """Check if a < b"""
    return a < b


def _lte(a, b):
    """Check if a <= b"""
    return a <= b


def _regex(value, pattern) -> bool:
    if value is None:
        return False
    match = re.search(pattern, value)
    if match is None:
        return False
    return True


operator = {'$regex': _regex, '$eq': _eq, '$gt': _gt, '$gte': _gte, '$lt': _lt, '$lte': _lte}


class RecFind:
    """Visititems class to find all objects with a certain attribute value"""

    def __init__(self, func: Callable, attribute, value, objfilter, ignore_attribute_error):
        self._func = func
        self._attribute = attribute
        self._value = value
        self.found_objects = []
        self.objfilter = objfilter
        self.ignore_attribute_error = ignore_attribute_error

    def __call__(self, name, h5obj):
        if self.objfilter:
            if not isinstance(h5obj, self.objfilter):
                return
        try:
            objattr = h5obj.__getattribute__(self._attribute)
            if self._func(objattr, self._value):
                self.found_objects.append(h5obj)
        except AttributeError as e:
            if not self.ignore_attribute_error:
                raise AttributeError(f'Unknown key "{self._attribute}". Must be "$basename" or a valid h5py object '
                                     f'attribute. '
                                     'You may also consider setting the object filter to "$Dataset" or "$Group" '
                                     'because e.g. filtering for "$shape" only works for datasets. '
                                     'If you dont want this error to be raised and ignored instead, '
                                     'pass "ignore_attribute_error=True" '
                                     f'Original h5py error: {e}') from e


class RecAttrFind:
    """Visititems class to find all objects with a certain attribute value"""

    def __init__(self, func: Callable, attribute, value, objfilter):
        self._func = func
        self._attribute = attribute
        self._value = value
        self.objfilter = objfilter
        self.found_objects = []

    def __call__(self, name, obj):
        if self.objfilter:
            if not isinstance(obj, self.objfilter):
                return
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


AV_SPECIAL_FILTERS = ('$basename', '$name')


def _h5find(h5obj: Union[h5py.Group, h5py.Dataset], qk, qv, recursive, objfilter, ignore_attribute_error: bool = False):
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
            if recursive:
                _skip = False
                if objfilter:
                    if not isinstance(h5obj, objfilter):
                        _skip = True
                if not _skip:
                    if qk in h5obj.attrs:
                        if operator[ok](h5obj.attrs[qk], ov):
                            found_objs.append(h5obj)
                rf = RecAttrFind(operator[ok], qk, ov, objfilter=objfilter)
                h5obj.visititems(rf)
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
            else:
                if qk in h5obj.attrs:
                    if operator[ok](h5obj.attrs[qk], ov):
                        found_objs.append(h5obj)
                for hv in h5obj.values():
                    if qk in hv.attrs:
                        if operator[ok](hv.attrs[qk], ov):
                            found_objs.append(hv)
    else:
        for ok, ov in qv.items():
            if recursive:
                rf = RecFind(operator[ok], qk[1:], ov, objfilter=objfilter,
                             ignore_attribute_error=ignore_attribute_error)
                rf(name='/', h5obj=h5obj)  # visit the root group
                h5obj.visititems(rf)  # will not visit the root group
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
            else:
                for hk, hv in h5obj.items():
                    if objfilter:
                        if not isinstance(hv, objfilter):
                            continue
                    if qk not in AV_SPECIAL_FILTERS and not ignore_attribute_error:
                        raise AttributeError(
                            f'Unknown key "{qk}". Must be one of these: {AV_SPECIAL_FILTERS}'
                            ' or a valid h5py object attribute. '
                            'You may also consider setting the object filter to "$Dataset" or "$Group" '
                            'because e.g. filtering for "$shape" only works for datasets. '
                            'If you dont want this error to be raised and ignored instead, '
                            'pass "ignore_attribute_error=True"')
                    try:
                        if qk == '$basename':
                            objattr = pathlib.Path(hv.__getattribute__('name')).name
                        else:
                            objattr = hv.__getattribute__(qk[1:])
                        if operator[ok](objattr, ov):
                            found_objs.append(hv)
                    except Exception as e:
                        raise Exception(f'Error while filtering for "{qk}" with "{ok}" and "{ov}"') from e
    return found_objs


def find(h5obj: Union[h5py.Group, h5py.Dataset],
         flt: Dict,
         objfilter: Union[h5py.Group, h5py.Dataset, None],
         recursive: bool,
         find_one: bool,
         ignore_attribute_error):
    """find objects in `h5obj` based on the filter request (-dictionary) `flt`"""
    # start with some input checks:
    if not isinstance(flt, Dict):
        raise TypeError(f'Filter must be a dictionary not {type(flt)}')
    objfilter = process_obj_filter_input(objfilter)

    # actual filter:
    results = []
    # go through all filter queries. They are treated as AND queries
    for k, v in flt.items():
        _results = _h5find(h5obj, k, v, recursive, objfilter, ignore_attribute_error)
        # if find_one:
        #     if len(_results):
        #         if objfilter:
        #             for r in _results:
        #                 if isinstance(r, objfilter):
        #                     return r
        #         return _results[0]
        results.append(_results)
    # only get common results from all results:
    common_results = list(set.intersection(*map(set, results)))

    if find_one:
        if len(common_results):
            return common_results[0]
        return  # Nothing found
    return common_results

    # if objfilter:
    #     return [r for r in common_results if isinstance(r, objfilter)]
    # return common_results


def distinct(h5obj: Union[h5py.Group, h5py.Dataset], key: str,
             objfilter: Union[h5py.Group, h5py.Dataset, None]) -> List[str]:
    """Return a distinct list of all found targets. A target generally is
    understood to be an attribute name. However, by adding a $ in front, class
    properties can be found, too, e.g. $shape will return all distinct shapes of the
    passed group."""
    objfilter = process_obj_filter_input(objfilter)
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


class File:
    """File as a database"""

    def __init__(self, filename: pathlib.Path, source_group='/', **kwargs):
        filename = pathlib.Path(filename)
        if not filename.is_file():
            raise ValueError(f'{filename} is not a file')
        self.filename = filename
        self.source_group = source_group
        self._kwargs = kwargs

    def __getitem__(self, item: str):
        return File(self.filename, source_group=item, **self._kwargs)

    def find(self, flt: Union[Dict, str],
             objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
             rec: bool = True,
             ignore_attribute_error: bool = False):
        """Find"""
        from .. import File
        if flt == {}:  # just find any!
            flt = {'$basename': {'$regex': '.*'}}
        with File(self.filename) as h5:
            return [lazy.lazy(r) for r in h5.find(flt, objfilter, rec, ignore_attribute_error)]

    def find_one(self,
                 flt: Union[Dict, str],
                 objfilter=None,
                 rec: bool = True,
                 ignore_attribute_error: bool = False):
        """Find one occurrence"""
        from .. import File
        with File(self.filename) as h5:
            return lazy.lazy(h5.find_one(flt, objfilter, rec, ignore_attribute_error))
