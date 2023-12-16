# """filequery module"""
#
# import h5py
# import numpy as np
# import pathlib
# import re
# from typing import List, Union, Dict, Callable
#
# from . import lazy
# from .interface import HDF5DatabaseInterface
# from ..utils import process_obj_filter_input
#
#
# # implementation similar to pymongo:
# # https://www.mongodb.com/docs/manual/reference/operator/query/
#
#
# class ResultList(list):
#
#     def find(self, *args, **kwargs):
#         """call find() on all entries"""
#         results = []
#         for r in self:
#             results.append(r.find_one(*args, **kwargs))
#         return ResultList(results)
#
#     def find_one(self, *args, **kwargs):
#         """call find_one() on all entries and return the first non-None result"""
#         for r in self:
#             result = r.find_one(*args, **kwargs)
#             if result:
#                 return result
#         return None
#
#
# def _eq(a, b):
#     """Check if a == b"""
#     return a == b
#
#
# def _arreq(a, b):
#     """Check if a == b"""
#     return np.array_equal(a, b)
#
#
# def _gt(a, b):
#     """Check if a > b"""
#     return a > b
#
#
# def _gte(a, b):
#     """Check if a >= b"""
#     return a >= b
#
#
# def _lt(a, b):
#     """Check if a < b"""
#     return a < b
#
#
# def _lte(a, b):
#     """Check if a <= b"""
#     return a <= b
#
#
# def _regex(value, pattern) -> bool:
#     if value is None:
#         return False
#     match = re.search(pattern, value)
#     if match is None:
#         return False
#     return True
#
#
# def _exists(value, tf: bool) -> bool:
#     if tf:
#         return value is not None
#     else:
#         return value is None
#
#
# operator = {'$regex': _regex, '$eq': _eq, '$gt': _gt, '$gte': _gte, '$lt': _lt, '$lte': _lte,
#             '$exists': _exists}
# value_operator = {'$eq': _arreq, '$gt': _gt, '$gte': _gte, '$lt': _lt, '$lte': _lte}
#
#
# class RecFind:
#     """Visititems class to find all objects with a certain attribute value"""
#
#     def __init__(self, func: Callable, attribute, value, objfilter, ignore_attribute_error):
#         self._func = func
#         self._attribute = attribute
#         self._value = value
#         self.found_objects = []
#         self.objfilter = objfilter
#         self.ignore_attribute_error = ignore_attribute_error
#
#     def __call__(self, name, h5obj):
#         if self.objfilter:
#             if not isinstance(h5obj, self.objfilter):
#                 return
#         try:
#             objattr = h5obj.__getattribute__(self._attribute)
#             if self._func(objattr, self._value):
#                 self.found_objects.append(h5obj)
#         except AttributeError as e:
#             if not self.ignore_attribute_error:
#                 raise AttributeError(f'Unknown key "{self._attribute}". Must be "$basename" or a valid h5py object '
#                                      f'attribute. '
#                                      'You may also consider setting the object filter to "$Dataset" or "$Group" '
#                                      'because e.g. filtering for "$shape" only works for datasets. '
#                                      'If you dont want this error to be raised and ignored instead, '
#                                      'pass "ignore_attribute_error=True" '
#                                      f'Original h5py error: {e}') from e
#
#
# class RecValueFind:
#     def __init__(self, transformer_func: Callable, comparison_func: Callable, comparison_value):
#         self._tfunc = transformer_func
#         self._cfunc = comparison_func
#         self._value = comparison_value
#         self._ndim = get_ndim(comparison_value)
#         self.objfilter = h5py.Dataset
#         self.found_objects = []
#
#     def __call__(self, name, obj):
#         if self.objfilter:
#             if not isinstance(obj, self.objfilter):
#                 return
#         transformed_value = self._tfunc(obj, self._value)
#         if transformed_value is not None:
#             if self._cfunc(transformed_value, self._value):
#                 self.found_objects.append(obj)
#
#
# class RecAttrFind:
#     """Visititems class to find all objects with a certain attribute value"""
#
#     def __init__(self, func: Callable, attribute, value, objfilter):
#         self._func = func
#         self._attribute = attribute
#         self._value = value
#         self.objfilter = objfilter
#         self.found_objects = []
#
#     def __call__(self, name, obj):
#         if self.objfilter:
#             if not isinstance(obj, self.objfilter):
#                 return
#         if '.' in self._attribute:
#             # dict comparison:
#             attr_name, dict_path = self._attribute.split('.', 1)
#             if attr_name in obj.attrs.raw:
#                 _attr_dict = dict(obj.attrs[attr_name])
#                 for _item in dict_path.split('.'):
#                     try:
#                         _attr_value = _attr_dict[_item]
#                     except KeyError:
#                         _attr_value = None
#                         break
#                 if _attr_value:
#                     if self._func(_attr_value, self._value):
#                         self.found_objects.append(obj)
#         elif self._attribute in obj.attrs.raw:
#             if self._func(obj.attrs.raw[self._attribute], self._value):
#                 self.found_objects.append(obj)
#
#
# class RecPropCollect:
#     """Visititems class to collect all class attributes matching a certain string"""
#
#     def __init__(self, attribute_name: str, objfilter: Union[h5py.Group, h5py.Dataset, None]):
#         self._attribute_name = attribute_name
#         self._objfilter = objfilter
#         self.found_objects = []
#
#     def __call__(self, name, obj):
#         if self._objfilter is None:
#             try:
#                 propval = obj.__getattribute__(self._attribute_name)
#                 self.found_objects.append(propval)
#             except AttributeError:
#                 pass
#         else:
#             if isinstance(obj, self._objfilter):
#                 try:
#                     propval = obj.__getattribute__(self._attribute_name)
#                     self.found_objects.append(propval)
#                 except AttributeError:
#                     pass
#
#
# class RecAttrCollect:
#     """Visititems class to collect all attributes matching a certain string"""
#
#     def __init__(self, attribute_name: str, objfilter: Union[h5py.Group, h5py.Dataset, None]):
#         self._attribute_name = attribute_name
#         self._objfilter = objfilter
#         self.found_objects = []
#
#     def __call__(self, name, obj):
#         if self._objfilter is None:
#             if self._attribute_name in obj.attrs.raw:
#                 self.found_objects.append(obj.attrs.raw[self._attribute_name])
#         else:
#             if isinstance(obj, self._objfilter):
#                 if self._attribute_name in obj.attrs.raw:
#                     self.found_objects.append(obj.attrs.raw[self._attribute_name])
#
#
# AV_SPECIAL_FILTERS = ('$basename', '$name')
#
#
# def _pass(obj, comparison_value):
#     if get_ndim(comparison_value) == obj.ndim:
#         return obj[()]
#     return None
#
#
# def _mean(obj, _):
#     if obj.dtype.char == 'S':
#         return None
#     return np.mean(obj[()])
#
#
# def get_ndim(value) -> int:
#     """Return the dimension of the input value. Scalars have dimension 0, other inputs are parsed with np.ndim()"""
#     if isinstance(value, (int, float)):
#         return 0
#     return np.ndim(value)
#
#
# math_operator = {'$eq': _pass,
#                  '$mean': _mean}
#
#
# def _h5find(h5obj: Union[h5py.Group, h5py.Dataset], qk, qv, recursive, objfilter, ignore_attribute_error: bool = False):
#     """
#
#     Parameters
#     ----------
#     h5obj: h5py.Group, h5py.Dataset
#         h5py object (group or dataset) to start search from
#
#     Returns
#     -------
#
#     """
#     found_objs = []
#
#     if qk in value_operator:
#         # user wants to compare qv to the value of the object
#
#         if not isinstance(qv, Dict):
#             qv = {'$eq': qv}
#
#         if len(qv) != 1:
#             raise ValueError(f'Cannot use operator "{qk}" for dict with more than one key')
#
#         if isinstance(h5obj, h5py.Dataset):
#             recursive = False
#
#         # h5obj is a group:
#         # assert isinstance(h5obj, h5py.Group)
#
#         for math_operator_name, comparison_value in qv.items():
#
#             if recursive:
#                 rf = RecValueFind(math_operator[math_operator_name], value_operator[qk], comparison_value)
#                 h5obj.visititems(rf)  # will not visit the root group
#                 for found_obj in rf.found_objects:
#                     found_objs.append(found_obj)
#             else:
#                 # iterator over all datasets in group
#                 if isinstance(h5obj, h5py.Group):
#                     iterator = h5obj.values()
#                 else:
#                     iterator = [h5obj]
#                 for target_obj in iterator:
#                     if isinstance(target_obj, h5py.Dataset):
#                         transformed_value = math_operator[math_operator_name](target_obj, comparison_value)
#                         if transformed_value is not None:
#                             if value_operator[qk](transformed_value, comparison_value):
#                                 found_objs.append(target_obj)
#             return found_objs
#
#         if isinstance(qv, (float, int)):
#             qv_ndim = 0
#         elif isinstance(qv, Dict):
#             if len(qv) != 1:
#                 raise ValueError(f'Cannot use operator "{qk}" for dict with more than one key')
#
#         else:
#             qv_ndim = np.ndim(qv)
#
#         if qv_ndim > 0 and qk != '$eq':
#             raise ValueError(f'Cannot use operator "{qk}" for non-scalar value "{qv}"')
#         if qk == '$eq':
#             qk = '$arreq'
#
#         if recursive:
#             rf = RecValueFind(operator[qk], qv, qv_ndim)
#             h5obj.visititems(rf)
#             for found_obj in rf.found_objects:
#                 found_objs.append(found_obj)
#         else:
#             for ds in h5obj.values():
#                 if isinstance(ds, h5py.Dataset):
#                     if ds.ndim == qv_ndim:
#                         if value_operator[qk](ds[()], qv):
#                             found_objs.append(ds)
#         return found_objs
#
#     is_hdf_attrs_search = qk[0] != '$'
#
#     if not isinstance(qv, Dict):
#         qv = {'$eq': qv}
#
#     # find objects with equal value
#     if is_hdf_attrs_search:
#         for ok, ov in qv.items():
#             if recursive:
#                 _skip = False
#                 if objfilter:
#                     if not isinstance(h5obj, objfilter):
#                         _skip = True
#                 if not _skip:
#                     if '.' in qk:
#                         # dict comparison:
#                         attr_name, dict_path = qk.split('.', 1)
#                         if attr_name in h5obj.attrs.raw:
#                             _attr_dict = dict(h5obj.attrs[attr_name])
#                             for _item in dict_path.split('.'):
#                                 try:
#                                     _attr_value = _attr_dict[_item]
#                                 except KeyError:
#                                     _attr_value = None
#                                     break
#                             if _attr_value:
#                                 if operator[ok](_attr_value, ov):
#                                     found_objs.append(h5obj)
#                     elif qk in h5obj.attrs.raw:
#                         if operator[ok](h5obj.attrs.raw[qk], ov):
#                             found_objs.append(h5obj)
#                 rf = RecAttrFind(operator[ok], qk, ov, objfilter=objfilter)
#                 h5obj.visititems(rf)
#                 for found_obj in rf.found_objects:
#                     found_objs.append(found_obj)
#             else:
#                 if qk in h5obj.attrs.raw:
#                     if operator[ok](h5obj.attrs.raw[qk], ov):
#                         found_objs.append(h5obj)
#                 if isinstance(h5obj, h5py.Group):
#                     for hv in h5obj.values():
#                         if qk in hv.attrs.raw:
#                             if operator[ok](hv.attrs.raw[qk], ov):
#                                 found_objs.append(hv)
#     else:
#         for ok, ov in qv.items():
#             if recursive:
#                 rf = RecFind(operator[ok], qk[1:], ov, objfilter=objfilter,
#                              ignore_attribute_error=ignore_attribute_error)
#                 rf(name='/', h5obj=h5obj)  # visit the root group
#                 h5obj.visititems(rf)  # will not visit the root group
#                 for found_obj in rf.found_objects:
#                     found_objs.append(found_obj)
#             else:
#                 if isinstance(h5obj, h5py.Dataset):
#                     iterator = [(h5obj.basename, h5obj), ]
#                 else:
#                     iterator = h5obj.items()
#                 for hk, hv in iterator:
#                     if objfilter:
#                         if not isinstance(hv, objfilter):
#                             continue
#                     if qk not in AV_SPECIAL_FILTERS and not ignore_attribute_error:
#                         raise AttributeError(
#                             f'Unknown key "{qk}". Must be one of these: {AV_SPECIAL_FILTERS}'
#                             ' or a valid h5py object attribute. '
#                             'You may also consider setting the object filter to "$Dataset" or "$Group" '
#                             'because e.g. filtering for "$shape" only works for datasets. '
#                             'If you dont want this error to be raised and ignored instead, '
#                             'pass "ignore_attribute_error=True"')
#                     try:
#                         if qk == '$basename':
#                             objattr = pathlib.Path(hv.__getattribute__('name')).name
#                         else:
#                             objattr = hv.__getattribute__(qk[1:])
#                         if operator[ok](objattr, ov):
#                             found_objs.append(hv)
#                     except Exception as e:
#                         raise Exception(f'Error while filtering for "{qk}" with "{ok}" and "{ov}"') from e
#     return found_objs
#
#
# def find(h5obj: Union[h5py.Group, h5py.Dataset],
#          flt: [Dict, str, List[str]],
#          objfilter: Union[h5py.Group, h5py.Dataset, None],
#          recursive: bool,
#          find_one: bool,
#          ignore_attribute_error):
#     if flt == {}:  # just find any!
#         flt = {'$basename': {'$regex': '.*'}}
#     if isinstance(flt, str):  # just find the attribute and don't filter for the value:
#         flt = {flt: {'$regex': '.*'}}
#     if isinstance(flt, List):
#         if all(isinstance(f, str) for f in flt):
#             flt = {f: {'$regex': '.*'} for f in flt}
#         else:
#             raise TypeError(f'Filter must be a dictionary, a string or a list of strings not {type(flt)}')
#     if not isinstance(flt, Dict):
#         raise TypeError(f'Filter must be a dictionary not {type(flt)}')
#     objfilter = process_obj_filter_input(objfilter)
#
#     # perform the filter process:
#     # ---------------------------
#     results = []
#     # go through all filter queries. They are treated as AND queries
#     for k, v in flt.items():
#         _results = _h5find(h5obj, k, v, recursive, objfilter, ignore_attribute_error)
#         results.append(_results)
#     # only get common results from all results:
#     common_results = list(set.intersection(*map(set, results)))
#
#     if find_one:
#         if len(common_results):
#             return common_results[0]
#         return  # Nothing found
#     return common_results
#
# def find_dpr(h5obj: Union[h5py.Group, h5py.Dataset],
#          flt: [Dict, str, List[str]],
#          objfilter: Union[h5py.Group, h5py.Dataset, None],
#          recursive: bool,
#          find_one: bool,
#          ignore_attribute_error) -> ResultList:
#     """find objects in `h5obj` based on the filter request (-dictionary) `flt`
#
#     A string instead of a dictionary for the parameter `flt` is also allowed. In this case, the string is used as
#     a regular expression to find objects with an attribute matching the regular expression '.*', so any object.
#
#
#     Examples
#     --------
#     >>> h5tbx.database.File(filename).find_one({'standard_name': {'$regex': '.*'}} '$dataset')
#     >>> # is equivalent to:
#     >>> h5tbx.database.File(filename).find_one('standard_name', '$dataset')
#
#     >>> h5tbx.database.File(filename).find_one({'standard_name': {'$regex': '.*'},
#     >>>                                         'units': {'$regex': '.*'}} '$dataset')
#     >>> # is equivalent to:
#     >>> h5tbx.database.File(filename).find_one(['standard_name', 'units'], '$dataset')
#     """
#     # start with some input checks:
#     if flt == {}:  # just find any!
#         flt = {'$basename': {'$regex': '.*'}}
#     if isinstance(flt, str):  # just find the attribute and don't filter for the value:
#         flt = {flt: {'$regex': '.*'}}
#     if isinstance(flt, List):
#         if all(isinstance(f, str) for f in flt):
#             flt = {f: {'$regex': '.*'} for f in flt}
#         else:
#             raise TypeError(f'Filter must be a dictionary, a string or a list of strings not {type(flt)}')
#     if not isinstance(flt, Dict):
#         raise TypeError(f'Filter must be a dictionary not {type(flt)}')
#     objfilter = process_obj_filter_input(objfilter)
#
#     # actual filter:
#     results = []
#     # go through all filter queries. They are treated as AND queries
#     for k, v in flt.items():
#         _results = _h5find(h5obj, k, v, recursive, objfilter, ignore_attribute_error)
#         # if find_one:
#         #     if len(_results):
#         #         if objfilter:
#         #             for r in _results:
#         #                 if isinstance(r, objfilter):
#         #                     return r
#         #         return _results[0]
#         results.append(_results)
#     # only get common results from all results:
#     common_results = list(set.intersection(*map(set, results)))
#
#     if find_one:
#         if len(common_results):
#             return common_results[0]
#         return  # Nothing found
#     return ResultList(common_results)
#
#     # if objfilter:
#     #     return [r for r in common_results if isinstance(r, objfilter)]
#     # return common_results
#
#
# def distinct(h5obj: Union[h5py.Group, h5py.Dataset], key: str,
#              objfilter: Union[h5py.Group, h5py.Dataset, None]) -> List[str]:
#     """Return a distinct list of all found targets. A target generally is
#     understood to be an attribute name. However, by adding a $ in front, class
#     properties can be found, too, e.g. $shape will return all distinct shapes of the
#     passed group."""
#     objfilter = process_obj_filter_input(objfilter)
#     if key[0] == '$':
#         rpc = RecPropCollect(key[1:], objfilter)
#
#         h5obj.visititems(rpc)
#         if objfilter:
#             if isinstance(h5obj, objfilter):
#                 try:
#                     propval = h5obj.__getattribute__(key[1:])
#                     rpc.found_objects.append(propval)
#                 except AttributeError:
#                     pass
#         else:
#             try:
#                 propval = h5obj.__getattribute__(key[1:])
#                 rpc.found_objects.append(propval)
#             except AttributeError:
#                 pass
#
#         return list(set(rpc.found_objects))
#
#     rac = RecAttrCollect(key, objfilter)
#     for k, v in h5obj.attrs.raw.items():
#         if k == key:
#             rac.found_objects.append(v)
#     if isinstance(h5obj, h5py.Group):
#         h5obj.visititems(rac)
#         if objfilter:
#             if isinstance(h5obj, objfilter):
#                 if key in h5obj.attrs.raw:
#                     rac.found_objects.append(h5obj.attrs.raw[key])
#         else:
#             if key in h5obj.attrs.raw:
#                 rac.found_objects.append(h5obj.attrs.raw[key])
#
#     return list(set(rac.found_objects))
#
#
# class NonInsertableDatabaseInterface:
#     """A database interface that does not allow inserting datasets"""
#
#     def insert_dataset(self, *args, **kwargs):
#         """Insert a dataset. This is not possible for an HDF5 file."""
#         raise NotImplementedError('By using an HDF5 file as a database, you cannot insert datasets')
#
#     def insert_group(self, *args, **kwargs):
#         """Insert a group. This is not possible for an HDF5 file."""
#         raise NotImplementedError('By using an HDF5 file as a database, you cannot insert groups')
#
#
# class H5ObjDB(HDF5DatabaseInterface, NonInsertableDatabaseInterface):
#     """HDF5 Group as a database"""
#
#     def __init__(self, group: h5py.Group):
#         self.src_group = group
#
#     def find_one(self,
#                  flt: Union[Dict, str],
#                  objfilter=None,
#                  rec: bool = True,
#                  ignore_attribute_error: bool = False) -> lazy.LHDFObject:
#         """Find one object in the group
#
#         Parameters
#         ----------
#         flt : Union[Dict, str]
#             The filter query similar to the pymongo syntax.
#         objfilter : Union[h5py.Group, h5py.Dataset, None]
#             If provided, only objects of this type will be returned.
#         rec : bool
#             If True, the search will be recursive. If False, only the current group
#             will be searched.
#         ignore_attribute_error : bool
#             If True, an AttributeError will be ignored if the attribute is not found.
#         """
#         return find(self.src_group, flt, objfilter, rec, ignore_attribute_error, find_one=True,)
#
#
# class File(HDF5DatabaseInterface, NonInsertableDatabaseInterface):
#     """File as a database"""
#
#     def __init__(self, filename: pathlib.Path, source_group='/', **kwargs):
#         filename = pathlib.Path(filename)
#         if not filename.is_file():
#             raise ValueError(f'{filename} is not a file')
#         self.filename = filename
#         self.source_group = source_group
#         self._kwargs = kwargs
#
#     def __getitem__(self, item: str):
#         return File(self.filename, source_group=item, **self._kwargs)
#
#     def find(self,
#              h5obj,
#              flt: Union[Dict, str],
#              objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
#              rec: bool = True,
#              ignore_attribute_error: bool = False):
#         """Find"""
#         from .. import File
#         with File(self.filename) as h5:
#             return ResultList([lazy.lazy(r) for r in find(h5obj, flt, objfilter, rec, ignore_attribute_error)])
#
#     def find_one(self,
#                  flt: Union[Dict, str],
#                  objfilter=None,
#                  rec: bool = True,
#                  ignore_attribute_error: bool = False):
#         """Find one occurrence"""
#         from .. import File
#         with File(self.filename) as h5:
#             return lazy.lazy(h5.find_one(flt, objfilter, rec, ignore_attribute_error))
