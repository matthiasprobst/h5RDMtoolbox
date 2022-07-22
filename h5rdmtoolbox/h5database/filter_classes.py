import h5py
import numpy as np


# @dataclass
# class HasDataset:
#     name: str
#     entry_grp: str = '/'
#
#     def search(self, root_group):
#         if not isinstance(root_group, h5py.Group):
#             raise ValueError(f'h5obj must be of type h5py.Group not "{type(root_group)}"')
#
#         if root_group.name != '/':
#             raise ValueError(f'Not a root group!')
#         if self.name in root_group:
#             return isinstance(root_group[self.name], h5py.Dataset)
#         return


# @dataclass
# class HasGroup:
#     name: str
#     entry_grp: str = '/'
#
#     def search(self, root_group):
#         if not isinstance(root_group, h5py.Group):
#             raise ValueError(f'h5obj must be of type h5py.Group not "{type(root_group)}"')
#
#         if root_group.name != '/':
#             raise ValueError(f'Not a root group!')
#         if self.name in root_group:
#             return isinstance(root_group[self.name], h5py.Group)
#         return


class EntryManager:

    def __getitem__(self, path):
        return H5RepoEntry(path)

    @property
    def attrs(self):
        return AttributeManager('/')


Entry = EntryManager()


class H5RepoEntry:

    def __init__(self, path='/'):
        self.path = path

    @property
    def attrs(self):
        return AttributeManager(self.path)

    def exists(self):
        return H5ObjectExist(self.path)

    def __getitem__(self, item):
        if isinstance(item, slice):
            # Dataset is sliced!
            return Dataset(self.path, _slice=item)


class H5ObjectExist:
    """Filter class that checks whether a HDF Object exists"""

    def __init__(self, path):
        self.path = path

    def search(self, h5grp):
        return self.path in h5grp


class AttributeManager:

    def __init__(self, path):
        self.path = path

    def __getitem__(self, name):
        self.name = name
        return Attr(self.path, name)


class AttrExists:
    """Filter class that checks whether a HDF Attribute exists"""

    def __init__(self, path, name):
        self.path = path
        self.name = name

    def search(self, h5grp):
        if self.path not in h5grp:
            return False
        h5obj = h5grp[self.path]
        return self.name in h5obj.attrs


class Attr:

    def __init__(self, path, name):
        self.path = path
        self.name = name
        self._func_calls = []
        self._cmp_func = None
        self._item = slice(None)

    def __eq__(self, other):
        self._cmp_func = ('eq', other)
        return self

    def __ne__(self, other):
        self._cmp_func = ('ne', other)
        return self

    def __ge__(self, other):
        self._cmp_func = ('ge', other)
        return self

    def __gt__(self, other):
        self._cmp_func = ('gt', other)
        return self

    def __le__(self, other):
        self._cmp_func = ('le', other)
        return self

    def __lt__(self, other):
        self._cmp_func = ('lt', other)
        return self

    def contains(self, key):
        """string comparison"""
        # if not isinstance(key, str):
        #     raise ValueError(f'Expecting a string for the "contains"-statement but got {type(key)}.')
        self._cmp_func = ('contains', key)
        return self

    def within(self, bounds):
        """Expecting a list or a tuple of two values. A tuple """
        if not isinstance(bounds, (tuple, list)):
            raise ValueError(f'Expecting a tuple or a list for the "within"-statement but got {type(bounds)}.')
        if not len(bounds) == 2:
            raise ValueError(f'Expecting a tuple or a list of length 2 not length {len(bounds)}.')
        if isinstance(bounds, tuple):
            self._cmp_func = ('within_exclude_bounds', bounds)
        else:  # list
            self._cmp_func = ('within_include_bounds', bounds)
        return self

    def exists(self):
        return AttrExists(self.path, self.name)

    def mean(self, *args, **kwargs):
        self._func_calls.append((np.mean, args, kwargs))
        return self

    def std(self, *args, **kwargs):
        self._func_calls.append((np.std, args, kwargs))
        return self

    def __getitem__(self, item):
        self._item = item
        return self

    def search(self, h5grp):
        if self.path not in h5grp:
            return False
        h5obj = h5grp[self.path]
        if self.name not in h5obj.attrs:
            return False
        attr_val = h5obj.attrs[self.name]

        if isinstance(attr_val, (np.bool_, int, float, np.int_)):
            arr = attr_val
        else:
            arr = h5obj.attrs[self.name].__getitem__(self._item)
            for func in self._func_calls:
                arr = func[0].__call__(arr, *func[1], **func[2])
            # self._func_calls = []

        if self._cmp_func is not None:
            if self._cmp_func[0] == 'eq':
                return arr == self._cmp_func[1]
            elif self._cmp_func[0] == 'ne':
                return arr != self._cmp_func[1]
            elif self._cmp_func[0] == 'gt':
                return arr > self._cmp_func[1]
            elif self._cmp_func[0] == 'ge':
                return arr >= self._cmp_func[1]
            elif self._cmp_func[0] == 'lt':
                return arr < self._cmp_func[1]
            elif self._cmp_func[0] == 'le':
                return arr <= self._cmp_func[1]
            elif self._cmp_func[0] == 'contains':
                return arr in self._cmp_func[1]
            elif self._cmp_func[0] == 'within_include_bounds':
                return self._cmp_func[1][0] <= arr <= self._cmp_func[1][1]
            elif self._cmp_func[0] == 'within_exclude_bounds':
                return self._cmp_func[1][0] < arr < self._cmp_func[1][1]

        return False


class Dataset:

    def __init__(self, name, _slice=None):
        self.name = name
        self._func_calls = []
        self._cmp_func = None
        if _slice is None:
            self._item = slice(None)
        else:
            self._item = _slice

    def __eq__(self, other):
        self._cmp_func = ('eq', other)
        return self

    def __ne__(self, other):
        self._cmp_func = ('ne', other)
        return self

    def __ge__(self, other):
        self._cmp_func = ('ge', other)
        return self

    def __gt__(self, other):
        self._cmp_func = ('gt', other)
        return self

    def __le__(self, other):
        self._cmp_func = ('le', other)
        return self

    def __lt__(self, other):
        self._cmp_func = ('lt', other)
        return self

    def mean(self, *args, **kwargs):
        self._func_calls.append((np.mean, args, kwargs))
        return self

    def std(self, *args, **kwargs):
        self._func_calls.append((np.std, args, kwargs))
        return self

    def abs(self, *args, **kwargs):
        self._func_calls.append((np.abs, args, kwargs))
        return self

    def __getitem__(self, item):
        self._item = item
        return self

    def search(self, h5grp):
        if not isinstance(h5grp, h5py.Group):
            raise TypeError(f'"{self.name} is not a group!')
        if self.name not in h5grp:
            return False
        arr = h5grp[self.name].__getitem__(self._item)
        for func in self._func_calls:
            arr = func[0].__call__(arr, *func[1], **func[2])
        # self._func_calls = []

        if self._cmp_func is not None:
            if self._cmp_func[0] == 'eq':
                if isinstance(arr, np.ndarray):
                    return np.array_equal(arr, self._cmp_func[1])
                return arr == self._cmp_func[1]
            elif self._cmp_func[0] == 'ne':
                if isinstance(arr, np.ndarray):
                    return not np.array_equal(arr, self._cmp_func[1])
                return arr != self._cmp_func[1]
            elif self._cmp_func[0] == 'gt':
                return arr > self._cmp_func[1]
            elif self._cmp_func[0] == 'ge':
                return arr >= self._cmp_func[1]
            elif self._cmp_func[0] == 'lt':
                return arr < self._cmp_func[1]
            elif self._cmp_func[0] == 'le':
                return arr <= self._cmp_func[1]
        return False
