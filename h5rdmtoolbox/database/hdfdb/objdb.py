import h5py
import numpy as np
from typing import Union, Dict, List, Callable, Generator

from . import query, utils
from .nonsearchable import NonInsertableDatabaseInterface
from .. import lazy
from ..template import HDF5DBInterface


def basename(name: str) -> str:
    """Return basename of a name, which is the last occurrence in
    a string with forward slashes"""
    return name.rsplit('/', 1)[-1]


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
            return
            if not self.ignore_attribute_error:
                raise AttributeError(f'HDF object {h5obj} has no attribute "{self._attribute}". You may add '
                                     'an objfilter, because dataset and groups dont share all attributes. '
                                     'One example is "dtype", which is only available with datasets') from e


class RecValueFind:
    def __init__(self, transformer_func: Callable, comparison_func: Callable, comparison_value):
        self._tfunc = transformer_func
        self._cfunc = comparison_func
        self._value = comparison_value
        self._ndim = query.get_ndim(comparison_value)
        self.objfilter = h5py.Dataset
        self.found_objects = []

    def __call__(self, name, obj):
        if self.objfilter:
            if not isinstance(obj, self.objfilter):
                return
        transformed_value = self._tfunc(obj, self._value)
        if transformed_value is not None:
            if self._cfunc(transformed_value, self._value):
                self.found_objects.append(obj)


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
        if '.' in self._attribute:
            # dict comparison:
            attr_name, dict_path = self._attribute.split('.', 1)
            if attr_name in obj.attrs:
                _attr_dict = dict(obj.attrs[attr_name])
                for _item in dict_path.split('.'):
                    try:
                        _attr_value = _attr_dict[_item]
                    except KeyError:
                        _attr_value = None
                        break
                if _attr_value:
                    if self._func(_attr_value, self._value):
                        self.found_objects.append(obj)
        if self._func(obj.attrs.get(self._attribute, None), self._value):
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

    if qk in query.value_operator:
        # user wants to compare qv to the value of the object

        if not isinstance(qv, Dict):
            qv = {'$eq': qv}

        if len(qv) != 1:
            raise ValueError(f'Cannot use query.operator "{qk}" for dict with more than one key')

        if isinstance(h5obj, h5py.Dataset):
            recursive = False

        # h5obj is a group:
        # assert isinstance(h5obj, h5py.Group)

        for math_operator_name, comparison_value in qv.items():

            if recursive:
                rf = RecValueFind(query.math_operator[math_operator_name], query.value_operator[qk], comparison_value)
                h5obj.visititems(rf)  # will not visit the root group
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
            else:
                # iterator over all datasets in group
                if isinstance(h5obj, h5py.Group):
                    iterator = h5obj.values()
                else:
                    iterator = [h5obj]
                for target_obj in iterator:
                    if isinstance(target_obj, h5py.Dataset):
                        transformed_value = query.math_operator[math_operator_name](target_obj, comparison_value)
                        if transformed_value is not None:
                            if query.value_operator[qk](transformed_value, comparison_value):
                                found_objs.append(target_obj)
            return found_objs

        if isinstance(qv, (float, int)):
            qv_ndim = 0
        elif isinstance(qv, Dict):
            if len(qv) != 1:
                raise ValueError(f'Cannot use query.operator "{qk}" for dict with more than one key')

        else:
            qv_ndim = np.ndim(qv)

        if qv_ndim > 0 and qk != '$eq':
            raise ValueError(f'Cannot use query.operator "{qk}" for non-scalar value "{qv}"')
        if qk == '$eq':
            qk = '$arreq'

        if recursive:
            rf = RecValueFind(query.operator[qk], qv, qv_ndim)
            h5obj.visititems(rf)
            for found_obj in rf.found_objects:
                found_objs.append(found_obj)
        else:
            for ds in h5obj.values():
                if isinstance(ds, h5py.Dataset):
                    if ds.ndim == qv_ndim:
                        if query.value_operator[qk](ds[()], qv):
                            found_objs.append(ds)
        return found_objs

    is_hdf_attrs_search = qk[0] != '$'

    if callable(qv):
        qv = {'$userdefined': qv}
    else:
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
                    if '.' in qk:
                        # dict comparison:
                        attr_name, dict_path = qk.split('.', 1)
                        if attr_name in h5obj.attrs:
                            _attr_dict = dict(h5obj.attrs[attr_name])
                            for _item in dict_path.split('.'):
                                try:
                                    _attr_value = _attr_dict[_item]
                                except KeyError:
                                    _attr_value = None
                                    break
                            if _attr_value:
                                if query.operator[ok](_attr_value, ov):
                                    found_objs.append(h5obj)
                    elif qk in h5obj.attrs:
                        if query.operator[ok](h5obj.attrs[qk], ov):
                            found_objs.append(h5obj)
                rf = RecAttrFind(query.operator[ok], qk, ov, objfilter=objfilter)
                h5obj.visititems(rf)
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
            else:
                if qk in h5obj.attrs:
                    if query.operator[ok](h5obj.attrs[qk], ov):
                        found_objs.append(h5obj)
                if isinstance(h5obj, h5py.Group):
                    for hv in h5obj.values():
                        if qk in hv.attrs:
                            if query.operator[ok](hv.attrs[qk], ov):
                                found_objs.append(hv)
    else:
        for ok, ov in qv.items():
            if recursive:
                rf = RecFind(query.operator[ok], qk[1:], ov, objfilter=objfilter,
                             ignore_attribute_error=ignore_attribute_error)
                rf(name='/', h5obj=h5obj)  # visit the root group
                h5obj.visititems(rf)  # will not visit the root group
                for found_obj in rf.found_objects:
                    found_objs.append(found_obj)
            else:
                if isinstance(h5obj, h5py.Dataset):
                    iterator = [(basename(h5obj.name), h5obj), ]
                else:
                    iterator = h5obj.items()
                for hk, hv in iterator:
                    if objfilter:
                        if not isinstance(hv, objfilter):
                            continue

                    if qk.startswith('$'):
                        try:
                            objattr = hv.__getattribute__(qk[1:])
                        except AttributeError:
                            if ignore_attribute_error:
                                continue
                            raise ValueError(f'No such attribute: {qk[1:]}.')

                    try:
                        if query.operator[ok](objattr, ov):
                            found_objs.append(hv)
                    except Exception as e:
                        raise Exception(f'Error while filtering for "{qk}" with "{ok}" and "{ov}"') from e
    return found_objs


def find(h5obj: Union[h5py.Group, h5py.Dataset],
         flt: [Dict, str, List[str]],
         objfilter: Union[h5py.Group, h5py.Dataset, None],
         recursive: bool,
         find_one: bool,
         ignore_attribute_error):
    if flt == {}:  # just find any!
        flt = {'$name': {'$regex': '.*'}}
    if isinstance(flt, str):  # just find the attribute and don't filter for the value:
        flt = {flt: {'$regex': '.*'}}
    if isinstance(flt, List):
        if all(isinstance(f, str) for f in flt):
            flt = {f: {'$regex': '.*'} for f in flt}
        else:
            raise TypeError(f'Filter must be a dictionary, a string or a list of strings not {type(flt)}')
    if not isinstance(flt, Dict):
        raise TypeError(f'Filter must be a dictionary not {type(flt)}')
    objfilter = utils.parse_obj_filter_input(objfilter)

    # perform the filter process:
    # ---------------------------
    results = []
    # go through all filter queries. They are treated as AND queries
    for k, v in flt.items():
        _results = _h5find(h5obj, k, v, recursive, objfilter, ignore_attribute_error)
        results.append(_results)
    # only get common results from all results:
    common_results = lazy.lazy(list(set.intersection(*map(set, results))))

    if find_one:
        if len(common_results):
            return common_results[0]
        return  # Nothing found
    return common_results


def distinct(h5obj: Union[h5py.Group, h5py.Dataset], key: str,
             objfilter: Union[h5py.Group, h5py.Dataset, None]) -> List[str]:
    """Return a distinct list of all found targets. A target generally is
    understood to be an attribute name. However, by adding a $ in front, class
    properties can be found, too, e.g. $shape will return all distinct shapes of the
    passed group."""
    objfilter = utils.parse_obj_filter_input(objfilter)
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
    for k, v in h5obj.attrs.raw.items():
        if k == key:
            rac.found_objects.append(v)
    if isinstance(h5obj, h5py.Group):
        h5obj.visititems(rac)
        if objfilter:
            if isinstance(h5obj, objfilter):
                if key in h5obj.attrs.raw:
                    rac.found_objects.append(h5obj.attrs.raw[key])
        else:
            if key in h5obj.attrs.raw:
                rac.found_objects.append(h5obj.attrs.raw[key])

    return list(set(rac.found_objects))


class ObjDB(NonInsertableDatabaseInterface, HDF5DBInterface):
    """HDF5 Group or Dataset as a database"""

    def __init__(self, obj: Union[h5py.Dataset, h5py.Group]):
        if isinstance(obj, h5py.Group):
            self.src_obj = h5py.Group(obj.id)
        elif isinstance(obj, h5py.Dataset):
            self.src_obj = h5py.Dataset(obj.id)
        else:
            raise TypeError(f'Unexpected type: {type(obj)}')

    def find_one(self,
                 flt: Union[Dict, str],
                 objfilter=None,
                 recursive: bool = True,
                 ignore_attribute_error: bool = False) -> lazy.LHDFObject:
        """Find one object in the obj

        Parameters
        ----------
        flt : Union[Dict, str]
            The filter query similar to the pymongo syntax.
        objfilter : Union[h5py.Group, h5py.Dataset, None]
            If provided, only objects of this type will be returned.
        recursive : bool
            If True, the search will be recursive. If False, only the current obj
            will be searched.
        ignore_attribute_error : bool
            If True, an AttributeError will be ignored if the attribute is not found.
        """
        if isinstance(self.src_obj, h5py.Dataset) and recursive:
            recursive = False
        return lazy.lazy(
            find(
                self.src_obj,
                flt=flt,
                objfilter=objfilter,
                recursive=recursive,
                find_one=True,
                ignore_attribute_error=ignore_attribute_error)
        )

    def find(self,
             flt: Union[Dict, str],
             objfilter=None,
             recursive: bool = True,
             ignore_attribute_error: bool = False) -> Generator[lazy.LHDFObject, None, None]:
        if isinstance(self.src_obj, h5py.Dataset) and recursive:
            recursive = False
        results = find(self.src_obj,
                       flt=flt,
                       objfilter=objfilter,
                       recursive=recursive,
                       find_one=False,
                       ignore_attribute_error=ignore_attribute_error)

        for r in results:
            yield r

    def distinct(self, key: str,
                 objfilter: Union[h5py.Group, h5py.Dataset, None]):
        """Return a distinct list of all found targets. A target generally is
        understood to be an attribute name. However, by adding a $ in front, class
        properties can be found, too, e.g. $shape will return all distinct shapes of the
        passed obj."""
        return distinct(h5obj=self.src_obj, key=key, objfilter=objfilter)
