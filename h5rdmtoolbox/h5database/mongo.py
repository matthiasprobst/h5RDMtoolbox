import json
from typing import List

import h5py
import numpy as np
import pymongo.collection

from ..h5wrapper.accessory import register_special_dataset
from ..h5wrapper.h5file import H5Dataset, H5Group


def type2mongo(value: any) -> any:
    """Convert numpy dtypes to int/float/list/..."""
    if isinstance(value, np.int_):
        return int(value)
    if isinstance(value, np.float_):
        return float(value)
    if isinstance(value, np.ndarray):
        return list(value)
    return value


@register_special_dataset('mongo', H5Group)
class MongoGroupAccessor:
    """Accessor for HDF5 datasets to Mongo DB"""

    def __init__(self, h5grp: H5Group):
        self._h5grp = h5grp

    def insert(self, collection: pymongo.collection.Collection, recursive: bool = False,
               include_dataset: bool = True, interpret_dict_attr: bool = True,
               ignore_attrs: List[str] = None) -> pymongo.collection.Collection:
        """Insert HDF group into collection"""
        if ignore_attrs is None:
            ignore_attrs = []

        grp = self._h5grp
        post = {"filename": str(grp.file.filename), "path": grp.name, 'hdfobj': 'group'}
        for ak, av in grp.attrs.items():
            if ak not in ignore_attrs:
                if not ak.isupper():
                    if isinstance(av, dict):
                        for _ak, _av in av.items():
                            post[_ak] = _av
                    else:
                        post[ak] = type2mongo(av)
        collection.insert_one(post)

        if recursive:
            include_dataset = True

        if include_dataset or recursive:
            for dsname, h5obj in grp.items():
                if isinstance(h5obj, h5py.Dataset):
                    if include_dataset:
                        h5obj.mongo.insert(axis=None, collection=collection,
                                           ignore_attrs=ignore_attrs)
                else:
                    if recursive:
                        h5obj.mongo.insert(collection, recursive=recursive,
                                           include_dataset=include_dataset,
                                           ignore_attrs=ignore_attrs)
        return collection


@register_special_dataset('mongo', H5Dataset)
class MongoDatasetAccessor:
    """Accessor for HDF5 datasets to Mongo DB"""

    def __init__(self, h5ds: H5Dataset):
        self._h5ds = h5ds

    def insert(self, axis, collection: pymongo.collection.Collection,
               ignore_attrs: List[str] = None) -> pymongo.collection.Collection:
        """!!!UNDER HEAVY CONSTRUCTION!!!

        Insert a dataset with all its attributes and slice

        let's say first an last axis have dim scales
        h5['mydataset'] --> shape: (4, 21, 25, 3)
        h5['mydataset'].mongo.insert(axis=(0, 3)
        """
        if ignore_attrs is None:
            ignore_attrs = []

        ds = self._h5ds

        if axis is None:
            post = {"filename": str(ds.file.filename), "path": ds.name,
                    "shape": ds.shape,
                    "ndim": ds.ndim,
                    'hdfobj': 'dataset'}

            for ak, av in ds.attrs.items():
                if ak not in ignore_attrs:
                    if ak == 'COORDINATES':
                        if isinstance(av, (np.ndarray, list)):
                            for c in av:
                                post[c] = float(ds.parent[c][()])
                        else:
                            post[av] = float(ds.parent[av][()])
                    else:
                        if not ak.isupper():
                            post[ak] = av
            collection.insert_one(post)
            return collection

        if axis == 0:
            for i in range(ds.shape[0]):

                post = {"filename": str(ds.file.filename), "path": ds.name,
                        "shape": ds.shape,
                        "ndim": ds.ndim,
                        'hdfobj': 'dataset',
                        'slice': ((i, i + 1, 1),
                                  (0, None, 1),
                                  (0, None, 1))}

                if len(ds.dims[axis]) > 0:
                    for iscale in range(len(ds.dims[axis])):
                        dim = ds.dims[axis][iscale]
                        scale = dim[i]
                        if isinstance(scale, int):
                            post[dim.name] = int(scale)
                        else:
                            post[dim.name] = float(scale)

                for ak, av in ds.attrs.items():
                    if ak not in ignore_attrs:
                        if ak == 'COORDINATES':
                            if isinstance(av, (np.ndarray, list)):
                                for c in av:
                                    post[c] = float(ds.parent[c][()])
                            else:
                                post[av] = float(ds.parent[av][()])
                        else:
                            if not ak.isupper():
                                post[ak] = av
                collection.insert_one(post)
                return collection
        else:
            raise ValueError(f'Only accepts axis==0 in this developmet stage')

# def write_to_db(filename, collection):
#     """Insert a dataset into a pymongo collection"""
#     img_meta_dicts = []
#
#     import h5py
#     with h5py.File(filename, 'r') as h5:
#         for iimg in range(ds.shape[0]):
#             post = {"filename": str(filename),
#                     "image_dataset_path": "/image",
#                     "nparticles": int(h5['nparticles'][iimg]),
#                     "slice": ((iimg, iimg+1, 1),
#                               (0, None, 1),
#                               (0, None, 1))
#                    }
#             collection.insert_one(post)
#     # db.list_collection_names()
