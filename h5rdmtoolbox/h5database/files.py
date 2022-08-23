import pathlib
from typing import Union, Any, Dict

import h5py

from ..h5wrapper import open_wrapper

names = []


def find_obj_by_name(root, dsname, recursive, h5obj):
    found_objs = []

    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if name == dsname:
                found_objs.append(node)

    if recursive:
        root.visititems(_get_ds)
        return found_objs

    if isinstance(root, h5obj):
        if dsname == root.name:
            found_objs.append(root)
        return found_objs

    for k, v in root.items():
        if isinstance(v, h5py.Dataset):
            if dsname == k:
                found_objs.append(v)
    return found_objs


def find_one_obj_by_name(root, dsname, recursive, h5obj):
    def _get_ds(name, node):
        if isinstance(node, h5obj):
            if name == dsname:
                return node

    if recursive:
        return root.visititems(_get_ds)
    if isinstance(root, h5obj):
        if dsname == root.name:
            return root
        else:
            return None
    for k, v in root.items():
        if isinstance(v, h5obj):
            if dsname == k:
                return v
    return None


def find_attributes(h5obj: Union[h5py.Group, h5py.Dataset],
                    attribute_name: str,
                    attribute_value: Any,
                    recursive: bool,
                    h5type: Union[str, None],
                    find_one: bool):
    """Find one or many attibute(s) recursively (or not) starting from a group or dataset"""

    def _get_grp(name, node):
        if isinstance(node, h5py.Group):
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
                if node.attrs[attribute_name] == attribute_value:
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
                    if ds.attrs[attribute_name] == attribute_value:
                        names.append(ds)
        elif h5type.lower() in ('dataset', 'ds'):
            for ds in h5obj.values():
                if isinstance(ds, h5py.Dataset):
                    if attribute_name in ds.attrs:
                        if ds.attrs[attribute_name] == attribute_value:
                            names.append(ds)
        elif h5type.lower() in ('group', 'grp', 'gr'):
            for ds in h5obj.values():
                if isinstance(ds, h5py.Group):
                    if attribute_name in ds.attrs:
                        if ds.attrs[attribute_name] == attribute_value:
                            names.append(ds)
    if find_one:
        return res
    return names


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
            if k == '$dataset':
                if find_one:
                    return find_one_obj_by_name(h5obj, v, recursive, h5py.Dataset)
                return find_obj_by_name(h5obj, v, recursive, h5py.Dataset)
            elif k == '$group':
                if find_one:
                    return find_one_obj_by_name(h5obj, v, recursive, h5py.Group)
                return find_obj_by_name(h5obj, v, recursive, h5py.Group)
        return find_attributes(h5obj, k, v, recursive=recursive, h5type=h5type, find_one=find_one)


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
