import h5py
import json
import numpy as np
from typing import Type
from typing import Union, Dict, List, Callable, Optional

from . import query, utils
from ..interface import HDF5DBInterface
from ...protocols import LazyDataset, LazyGroup, LazyObject
from .. import lazy


def basename(name: str) -> str:
    """Return basename of a name, which is the last occurrence in
    a string with forward slashes"""
    return name.rsplit('/', 1)[-1]


class RecFind:
    """Visititems class to find all objects with a certain attribute value"""

    def __init__(self, func: Callable, attribute, value, objfilter, ignore_attribute_error):
        self._func = func
        self._attribute = attribute
        if isinstance(value, set):
            raise TypeError(
                'It seems that your query has a typo. Expecting a dictionary or base string or number but got '
                f'a set: {value}'
            )
        # if isinstance(value, dict):
        #     _operators = query.operator.get(k) for k in value.keys()
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
        except AttributeError:
            return
            # if not self.ignore_attribute_error:
            #     raise AttributeError(f'HDF object {h5obj} has no attribute "{self._attribute}". You may add '
            #                          'an objfilter, because dataset and groups dont share all attributes. '
            #                          'One example is "dtype", which is only available with datasets') from e


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
            attr_value = obj.attrs.get(attr_name, None)
            if attr_value is not None:
                if isinstance(attr_value, str) and attr_value.startswith('{') and attr_value.endswith('}'):
                    _attr_dict = json.loads(attr_value)

                    _attr_value = None
                    for _item in dict_path.split('.'):
                        try:
                            _attr_value = _attr_dict[_item]
                        except KeyError:
                            break

                    if _attr_value:
                        if self._func(_attr_value, self._value):
                            self.found_objects.append(obj)

        if self._func(obj.attrs.get(self._attribute, None), self._value):
            self.found_objects.append(obj)


class RecPropCollect:
    """Visititems class to collect all class attributes matching a certain string"""

    def __init__(self, attribute_name: str, objfilter: Optional[Union[Type[h5py.Dataset], Type[h5py.Group]]]):
        self._attribute_name = attribute_name
        self._objfilter = objfilter
        self.found_objects = []

    def __call__(self, name: str, obj: Union[h5py.Group, h5py.Dataset]):
        if self._objfilter is None:
            try:
                property_value = obj.__getattribute__(self._attribute_name)
                self.found_objects.append(property_value)
            except AttributeError:
                pass
        else:
            if isinstance(obj, self._objfilter):
                try:
                    property_value = obj.__getattribute__(self._attribute_name)
                    self.found_objects.append(property_value)
                except AttributeError:
                    pass


class RecAttrCollect:
    """Visititems class to collect all attributes matching a certain string"""

    def __init__(self, attribute_name: str, objfilter: Optional[Union[Type[h5py.Dataset], Type[h5py.Group]]]):
        self._attribute_name = attribute_name
        self._objfilter = objfilter
        self.found_objects = []

    def __call__(self, name: str, obj: Union[h5py.Group, h5py.Dataset]):
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

    if qk == '$basename':
        qk = '$name'
        assert isinstance(qv, str), 'Expected {$basename: "search value"} but value is not a string'
        qv = {'$basename': qv}

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

        if isinstance(qv, Dict) and len(qv) != 1:
            raise ValueError(f'Cannot use query.operator "{qk}" for dict with more than one key')

        if isinstance(qv, (float, int)):
            qv_ndim = 0
        else:
            assert isinstance(qv, (str, np.ndarray)), f'Unexpected type: {type(qv)}'
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
                            _attr_value = None
                            for _item in dict_path.split('.'):
                                try:
                                    _attr_value = _attr_dict[_item]
                                except KeyError:
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
                # rf(name=h5obj.name, h5obj=h5obj)  # visit the root group
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
                            raise Exception(f'Error while filtering for "{qk}" with "{ok}" and "{ov}": {e}')
    return found_objs


ListOfLazyObjs = List[Union[LazyDataset, LazyGroup]]


def find(h5obj: Union[h5py.Group, h5py.Dataset],
         flt: Union[Dict, str, List[str]],
         objfilter: Union[h5py.Group, h5py.Dataset, None],
         recursive: bool,
         find_one: bool,
         ignore_attribute_error) -> Optional[Union[List[LazyObject], LazyObject]]:
    """Find datasets or groups in an object.

    Parameters
    ----------
    h5obj: Group or Dataset
        obj from where to start searching
    flt: Union[Dict, str, List[str]]
        The filter query similar to the pymongo syntax.
    objfilter: Optional
        Filter only for dataset or group. if None, consider both types.
    recursive: bool
        Whether to recursively search in subgroups, too
    find_one: bool
        If True, the first search result is returned
    ignore_attribute_error: bool
        If True, attribute errors are ignored.

    Examples
    --------
    >>> from h5rdmtoolbox.database import hdfdb
    >>> with h5tbx.File(filename) as h5:
    ...     # find the obj with standard_name=='x_velocity':
    ...     hdfdb.ObjDB(h5).find({'standard_name': 'x_velocity'})
    ...     # all datasets must be gzip-compressed:
    ...     hdfdb.ObjDB(h5).find({'$compression': 'gzip'}, objfilter='dataset')
    """
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


def distinct(h5obj: Union[h5py.Group, h5py.Dataset],
             key: str,
             objfilter: Optional[Union[Type[h5py.Group], Type[h5py.Dataset]]]) -> List[str]:
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
                    property_value = h5obj.__getattribute__(key[1:])
                    rpc.found_objects.append(property_value)
                except AttributeError:
                    pass
        else:
            try:
                property_value = h5obj.__getattribute__(key[1:])
                rpc.found_objects.append(property_value)
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


class ObjDB(HDF5DBInterface):
    """HDF5 Group or Dataset as a database"""

    def __init__(self, obj: Union[h5py.Dataset, h5py.Group]):
        if isinstance(obj, h5py.Group):
            self.src_obj = h5py.Group(obj.id)
        elif isinstance(obj, h5py.Dataset):
            self.src_obj = h5py.Dataset(obj.id)
        else:
            raise TypeError(f'Unexpected type: {type(obj)}')
        self.find = self._instance_find  # allow `find` to be a static method and instance method
        self.rdf_find = self._instance_rdf_find  # allow `find` to be a static method and instance method
        self.find_one = self._instance_find_one  # allow `find_one` to be a static method and instance method

    @staticmethod
    def find_one(obj: Union[h5py.Dataset, h5py.Group], *args, **kwargs) -> Union[LazyObject]:
        """Please refer to the docstring of the find_one method of the ObjDB class"""
        return ObjDB(obj).find_one(*args, **kwargs)

    @staticmethod
    def find(obj: Union[h5py.Dataset, h5py.Group], *args, **kwargs) -> List[LazyObject]:
        """Please refer to the docstring of the find_one method of the ObjDB class"""
        return ObjDB(obj).find(*args, **kwargs)

    def _instance_find_one(self,
                           flt: Union[Dict, str],
                           objfilter=None,
                           recursive: bool = True,
                           ignore_attribute_error: bool = False) -> LazyObject:
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

        return find(
            self.src_obj,
            flt=flt,
            objfilter=objfilter,
            recursive=recursive,
            find_one=True,
            ignore_attribute_error=ignore_attribute_error
        )

    def _instance_find(self,
                       flt: Union[Dict, str],
                       objfilter=None,
                       recursive: bool = True,
                       ignore_attribute_error: bool = False) -> List[LazyObject]:
        if isinstance(self.src_obj, h5py.Dataset) and recursive:
            recursive = False
        results = find(self.src_obj,
                       flt=flt,
                       objfilter=objfilter,
                       recursive=recursive,
                       find_one=False,
                       ignore_attribute_error=ignore_attribute_error)
        return results

    def _instance_rdf_find(self, *,
                           rdf_subject: Optional[str] = None,
                           rdf_type: Optional[str] = None,
                           rdf_predicate: Optional[str] = None,
                           rdf_object: Optional[str] = None,
                           recursive: bool = True) -> Optional[List[Union[LazyDataset, LazyGroup]]]:
        """Find objects based on rdf triples"""
        import h5rdmtoolbox as h5tbx
        if isinstance(self.src_obj, h5py.Group):
            src_obj = h5tbx.Group(self.src_obj)
        else:
            src_obj = h5tbx.Dataset(self.src_obj)
        return lazy.lazy(src_obj.rdf.find(rdf_subject=rdf_subject,
                                          rdf_type=rdf_type,
                                          rdf_predicate=rdf_predicate,
                                          rdf_object=rdf_object,
                                          recursive=recursive))

    def distinct(self, key: str,
                 objfilter: Optional[Union[h5py.Group, h5py.Dataset]] = None):
        """Return a distinct list of all found targets. A target generally is
        understood to be an attribute name. However, by adding a $ in front, class
        properties can be found, too, e.g. $shape will return all distinct shapes of the
        passed obj."""
        return distinct(h5obj=self.src_obj, key=key, objfilter=objfilter)
