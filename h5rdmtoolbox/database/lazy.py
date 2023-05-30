"""lazy objects. user can work with datasets and groups without having to open the file him/her-self"""
import h5py
from typing import Union


class LAttributeManager:
    """Lazy Attribute Manager"""

    def __init__(self, attrs):
        self.attrs = attrs

    def __getitem__(self, item):
        return self.attrs[item]

    def __repr__(self):
        return repr(self.attrs)

    def keys(self):
        return self.attrs.keys()

    def values(self):
        return self.attrs.values()


class LGroup:
    """Lazy Group"""

    def __init__(self, filename, name, attrs, properties):
        self.filename = filename
        self.name = name
        self._attrs = attrs
        self.properties = properties

    def __getattr__(self, item):
        if item in self.properties:
            return self.properties[item]
        return super().__getattribute__(item)

    @property
    def attrs(self) -> LAttributeManager:
        """Return the attributes of the group as a LAttributeManager object"""
        return LAttributeManager(self._attrs)


class LDataset(LGroup):
    """Lazy Dataset"""

    def __getitem__(self, item):
        from .. import File
        with File(self.filename, mode='r') as h5:
            return h5[self.name][item]


def _get_dataset_properties(h5obj):
    return dict(ndim=h5obj.ndim,
                shape=h5obj.shape,
                dtype=h5obj.dtype,
                size=h5obj.size,
                chunks=h5obj.chunks,
                compression=h5obj.compression,
                compression_opts=h5obj.compression_opts,
                shuffle=h5obj.shuffle,
                fletcher32=h5obj.fletcher32,
                maxshape=h5obj.maxshape,
                fillvalue=h5obj.fillvalue,
                scaleoffset=h5obj.scaleoffset,
                external=h5obj.external)


def lazy(h5obj) -> Union[LDataset, LGroup]:
    """Make a lazy object from a h5py object"""
    if isinstance(h5obj, h5py.Group):
        return LGroup(h5obj.file.filename, h5obj.name, dict(h5obj.attrs), {})
    elif isinstance(h5obj, h5py.Dataset):
        return LDataset(h5obj.file.filename, h5obj.name, dict(h5obj.attrs), _get_dataset_properties(h5obj))
    raise TypeError(f'Cannot make {type(h5obj)} lazy')