import pathlib
import re
from typing import Union, Any, Dict, Callable

import h5py

from ..h5wrapper import open_wrapper


def find_obj_by_property(root, target_value, recursive, h5obj, cmp_func):

    found_objs = []

    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if cmp_func(node, target_value):
                found_objs.append(node)

    if recursive:
        root.visititems(_get_ds)
        return found_objs

    if isinstance(root, h5obj):
        if cmp_func(root, target_value):
            found_objs.append(root)
        return found_objs
    raise TypeError(f'Shape can only be checked for datasets not {type(root)}')


def find_one_obj_by_property(root, target_value, recursive, h5obj, cmp_func):

    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if cmp_func(node, target_value):
                return node

    if recursive:
        return root.visititems(_get_ds)

    if isinstance(root, h5obj):
        if cmp_func(root, target_value):
            return root
    raise TypeError(f'Shape can only be checked for datasets not {type(root)}')


def find_obj_by_name(root, objname, recursive, h5obj, cmp: Callable):
    found_objs = []

    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if cmp(name, objname):
                found_objs.append(node)

    if recursive:
        root.visititems(_get_ds)
        return found_objs

    if isinstance(root, h5obj):
        if cmp(root.name, objname):
            found_objs.append(root)
        return found_objs

    for k, v in root.items():
        if isinstance(v, h5obj):
            if cmp(k, objname):
                found_objs.append(v)
    return found_objs


def find_one_obj_by_name(root, objname, recursive, h5obj, cmp: Callable):
    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if cmp(name, objname):
                return node

    if recursive:
        return root.visititems(_get_ds)
    if isinstance(root, h5obj):
        if cmp(root.name, objname):
            return root
        else:
            return None
    for k, v in root.items():
        if isinstance(v, h5obj):
            if cmp(k, objname):
                return v
    return None


def find_attributes(h5obj: Union[h5py.Group, h5py.Dataset],
                    attribute_name: str,
                    attribute_value: Any,
                    recursive: bool,
                    h5type: Union[str, None],
                    find_one: bool,
                    cmp: Callable):
    """Find one or many attibute(s) recursively (or not) starting from a group or dataset"""
    names = []

    def _get_grp(name, node):
        if isinstance(node, h5py.Group):
            if attribute_name in node.attrs:
                if attribute_value is None:
                    if find_one:
                        return node
                    names.append(node)
                else:
                    if cmp(node.attrs[attribute_name], attribute_value):
                        if find_one:
                            return node
                        names.append(node)

    def _get_ds(name, node):
        if isinstance(node, h5py.Dataset):
            if attribute_name in node.attrs:
                if attribute_value is None:
                    if find_one:
                        return node
                    names.append(node)
                else:
                    if node.attrs[attribute_name] == attribute_value:
                        if find_one:
                            return node
                        names.append(node)

    def _get_ds_grp(name, node):
        if attribute_name in node.attrs:
            if attribute_value is None:
                if find_one:
                    return node
                names.append(node)
            else:
                if cmp(node.attrs[attribute_name], attribute_value):
                    if find_one:
                        return node
                    names.append(node)

    if recursive:
        if h5type is None:
            res = h5obj.visititems(_get_ds_grp)
        elif h5type.lower() in ('dataset', 'ds'):
            res = h5obj.visititems(_get_ds)
        elif h5type.lower() in ('group', 'grp', 'gr'):
            res = h5obj.visititems(_get_grp)
    else:
        if h5type is None:
            for ds in h5obj.values():
                if attribute_name in ds.attrs:
                    if cmp(ds.attrs[attribute_name], attribute_value):
                        names.append(ds)
        elif h5type.lower() in ('dataset', 'ds'):
            for ds in h5obj.values():
                if isinstance(ds, h5py.Dataset):
                    if attribute_name in ds.attrs:
                        if cmp(ds.attrs[attribute_name], attribute_value):
                            names.append(ds)
        elif h5type.lower() in ('group', 'grp', 'gr'):
            for ds in h5obj.values():
                if isinstance(ds, h5py.Group):
                    if attribute_name in ds.attrs:
                        if cmp(ds.attrs[attribute_name], attribute_value):
                            names.append(ds)
    if find_one:
        return res
    return names


# implementation similar to pymongo:
# https://www.mongodb.com/docs/manual/reference/operator/query/

def _eq(a, b):
    return a == b


def _any_str(a, b):
    return True


def _gt(a, b):
    return a > b


def _gte(a, b):
    return a >= b


def _lt(a, b):
    return a < b


def _lte(a, b):
    return a <= b


def _regex(inputstr, pattern):
    return re.search(pattern, inputstr)


def _eq_name(node, name):
    return node.name == name


def _eq_basename(node, name):
    return node.basename == name


def _eq_ndim(node, ndim):
    return node.ndim == ndim


def _eq_shape(node, shape):
    return node.shape == shape


_ds_flt = {'$name': _eq_name,
           '$basename': _eq_basename,
           '$ndim': _eq_ndim,
           '$shape': _eq_shape}
_cmp = {'$eq': _eq,
        '$gt': _gt,
        '$gte': _gte,
        '$lt': _lt,
        '$lte': _lte,
        '$regex': _regex}

_h5type = {'$dataset': h5py.Dataset,
           '$group': h5py.Group}


def find(h5obj: Union[h5py.Group, h5py.Dataset], flt, recursive: bool,
         h5type: Union[str, None],
         find_one: bool):
    if not isinstance(flt, Dict):
        raise TypeError(f'Filter must be a dictionary not {type(flt)}')
    # theoretically we could allow to filter for multiple conditions. Currently length of dict is limited to one
    if not len(flt) == 1:
        raise NotImplementedError('Currently it is only allowed to filter for one condition')
    for k, v in flt.items():
        if k[0] == '$':
            if isinstance(v, dict):
                if len(v) != 1:
                    raise NotImplementedError('Currently it is only allowed to filter for one condition')
                if find_one:
                    for _condition, _value in v.items():
                        if _condition[0] == '$':
                            if _condition not in ('$basename', '$name'):
                                # some conditions cannot be checked for groups:
                                if _h5type[k] == h5py.Group:
                                    raise RuntimeError(f'Cannot process {_condition} on groups!')
                            return find_one_obj_by_property(h5obj, _value, recursive, _h5type[k], _ds_flt[_condition])
                        return find_one_obj_by_name(h5obj, _value, recursive, _h5type[k], cmp=_cmp[_condition])
                for _condition, _value in v.items():
                    if _condition[0] == '$':
                        if _condition not in ('$basename', '$name'):
                            # some conditions cannot be checked for groups:
                            if _h5type[k] == h5py.Group:
                                raise RuntimeError(f'Cannot process {_condition} on groups!')
                        return find_obj_by_property(h5obj, _value, recursive, _h5type[k], _ds_flt[_condition])
                    return find_obj_by_name(h5obj, _value, recursive, _h5type[k], cmp=_cmp[_condition])
            if not isinstance(v, (str, dict)):
                raise TypeError(f'Value must be of type str or dict not {type(v)}')
            if find_one:
                if v == '':
                    return find_one_obj_by_name(h5obj, v, recursive, _h5type[k], cmp=_any_str)
                return find_one_obj_by_name(h5obj, v, recursive, _h5type[k], cmp=_eq)
            if v == '':
                return find_obj_by_name(h5obj, v, recursive, _h5type[k], cmp=_any_str)
            return find_obj_by_name(h5obj, v, recursive, _h5type[k], cmp=_eq)
        if isinstance(v, dict):
            if len(v) != 1:
                raise NotImplementedError('Currently it is only allowed to filter for one condition')
            # e.g. {'$gte': 1}
            # e.g. {'$regex': '^hallo[0-9]$'}
            for kcmp, vcmp in v.items():
                return find_attributes(h5obj, k, vcmp, recursive=recursive, h5type=h5type, find_one=find_one,
                                       cmp=_cmp[kcmp])
        return find_attributes(h5obj, k, v, recursive=recursive, h5type=h5type, find_one=find_one,
                               cmp=_eq)


class H5Files:
    """H5File-like interface for multiple HDF Files"""

    def __init__(self, *filenames, h5wrapper=None):
        self._list_of_filenames = [pathlib.Path(f) for f in filenames]
        self._opened_files = {}
        self._h5wrapper = h5wrapper

    def __getitem__(self, item):
        return self._opened_files[item]

    def __enter__(self):
        for filename in self._list_of_filenames:
            try:
                if self._h5wrapper is None:
                    h5file = open_wrapper(filename, mode='r')
                else:
                    h5file = self._h5wrapper(filename, mode='r')
                self._opened_files[filename.stem] = h5file
            except RuntimeError:
                for h5file in self._opened_files.values():
                    h5file.close()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def keys(self):
        """Return all opened filename stems"""
        return self._opened_files.keys()

    def close(self):
        """Close all opened files"""
        for h5file in self._opened_files.values():
            h5file.close()
