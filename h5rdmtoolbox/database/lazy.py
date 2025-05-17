"""lazy objects. user can work with datasets and groups without having to open the file him/her-self"""
import pathlib
from typing import Union, List, Dict, Optional

import h5py

from h5rdmtoolbox.protected_attributes import COORDINATES
from h5rdmtoolbox.protocols import LazyObject


class LHDFObject:
    """Lazy HDF object. This object is a proxy for an HDF object (dataset or group) that returns data
    on-demand. This means, that the file is opened when the object is accessed and closed when the object
    is no longer needed. This is useful for working with large files, where the user does not want to
    open the file manually, but still wants to work with the dataset.
    """

    def __init__(self, obj: Union[h5py.Group, h5py.Dataset]):
        self.filename = pathlib.Path(obj.file.filename)
        self._attrs = dict(obj.attrs)
        self.name = obj.name
        self._file = None

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}" in "{self.filename}">'

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        if isinstance(other, h5py.Dataset):
            other_filename = pathlib.Path(other.file.filename)
        else:
            other_filename = other.filename
        return self.name == other.name and self.filename == other_filename and self.attrs == other.attrs

    def __enter__(self):
        from .. import File
        self._file = File(self.filename)
        return self._file[self.name]

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    @property
    def basename(self) -> str:
        """Return the basename of the object"""
        return self.name.rsplit('/', 1)[1]

    @property
    def parentname(self) -> str:
        """Return the parent name of the object path"""
        return self.name.rsplit('/', 1)[0]

    @property
    def parentnames(self) -> List[str]:
        """Return the parent names of the object path"""
        return self.parentname.split('/')[1:]  # first is '', so skip

    @property
    def attrs(self) -> Dict:
        """Return the attributes of the group as a LAttributeManager object"""
        return self._attrs

    @property
    def hdf_filename(self):
        """Return the hdf filename"""
        return self.filename


class LGroup(LHDFObject):
    """Lazy Group"""

    def __init__(self, obj: h5py.Group):
        super().__init__(obj)

        self._children = {}
        for k, v in obj.items():
            if isinstance(v, h5py.Group):
                self._children[k] = LGroup(v)
                if ' ' not in k and not hasattr(self, k):
                    setattr(self, k, self._children[k])
            elif isinstance(v, h5py.Dataset):
                self._children[k] = LDataset(v)
                if ' ' not in k and not hasattr(self, k):
                    setattr(self, k, self._children[k])

    def keys(self):
        """Return the keys of the group which are the names of datasets and groups"""
        return self._children.keys()

    def __getitem__(self, item: str):
        if item in self._children:
            return self._children[item]
        raise KeyError(f'No such item: {item}. Known items: {self.keys()}')


class LDataset(LHDFObject):
    """Lazy Dataset"""

    def __init__(self, obj: h5py.Dataset):
        super().__init__(obj)
        # self.name = obj.name  # parent class already has this
        self.ndim = obj.ndim
        self.shape = obj.shape
        self.dtype = obj.dtype
        self.size = obj.size
        self.chunks = obj.chunks
        self.compression = obj.compression
        self.compression_opts = obj.compression_opts
        self.shuffle = obj.shuffle
        self.fletcher32 = obj.fletcher32
        self.maxshape = obj.maxshape
        self.fillvalue = obj.fillvalue
        self.scaleoffset = obj.scaleoffset
        self.external = obj.external
        _coords = obj.attrs.get(COORDINATES, None)
        if _coords is None:
            self._coords = []
        else:
            self._coords = list(_coords)
        for dim in obj.dims:
            for i in range(len(dim)):
                self._coords.append(lazy(dim[i]))
        self._file = None

    def __repr__(self):
        attrs_str = ', '.join({f'{k}={v}' for k, v in self.attrs.items() if not k.isupper()})
        return f'<LDataset "{self.name}" in "{self.filename}" attrs=({attrs_str})>'

    def __getitem__(self, item):
        from .. import File
        with File(self.filename, mode='r') as h5:
            return h5[self.name][item]

    @property
    def coords(self):
        return self._coords

    def isel(self, **indexers):
        from .. import File
        with File(self.filename) as h5:
            return h5[self.name].isel(**indexers)

    def sel(self, **coords):
        from .. import File
        with File(self.filename) as h5:
            return h5[self.name].sel(**coords)

    # def find(self, flt: Union[Dict, str],
    #          objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
    #          ignore_attribute_error: bool = False):
    #     """Find"""
    #     return super().find(flt, objfilter, rec=False, ignore_attribute_error=ignore_attribute_error)
    #
    # def find_one(self,
    #              flt: Union[Dict, str],
    #              objfilter=None,
    #              ignore_attribute_error: bool = False):
    #     """Find one occurrence"""
    #     return super().find_one(flt, objfilter, rec=False, ignore_attribute_error=ignore_attribute_error)


LazyInput = Union[h5py.Group, h5py.Dataset, LHDFObject, List[Union[h5py.Group, h5py.Dataset, LHDFObject]]]


def lazy(h5obj: LazyInput) -> Optional[Union[List[LazyObject], LHDFObject, LazyObject]]:
    """Make a lazy object from a h5py object"""
    if isinstance(h5obj, (LDataset, LGroup)):
        return h5obj
    if isinstance(h5obj, list):
        return [lazy(i) for i in h5obj]
    if h5obj is None:
        return None
    if isinstance(h5obj, h5py.Group):
        return LGroup(h5obj)
    elif isinstance(h5obj, h5py.Dataset):
        return LDataset(h5obj)
    # elif isinstance(h5obj, (tuple, list)):
    #     # expecting h5obj=(filename, obj_name)
    #     with h5py.File(h5obj[0]) as h5:
    #         return lazy(h5[h5obj[1]])
    raise TypeError(f'Cannot make {type(h5obj)} lazy')
