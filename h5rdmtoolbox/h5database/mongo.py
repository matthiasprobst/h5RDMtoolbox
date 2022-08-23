import pathlib
import warnings
from datetime import datetime, timezone
from typing import Dict
from typing import List

import h5py
import numpy as np
import pymongo.collection

from ..h5wrapper.accessory import register_special_dataset
from ..h5wrapper.h5file import H5Dataset, H5Group


def get_file_creation_time(filename: str) -> datetime:
    """Return the creation time of the passed filename"""
    return datetime.fromtimestamp(pathlib.Path(filename).stat().st_ctime, tz=timezone.utc)


def make_dict_mongo_compatible(dictionary: Dict):
    """Make the values of a dictionary compatible with mongo DB"""
    for ak, av in dictionary.items():
        if isinstance(av, (int, float, str)):
            pass
        elif isinstance(av, dict):
            dictionary[ak] = make_dict_mongo_compatible(av)
        else:
            try:
                if np.issubdtype(av, np.floating):
                    dictionary[ak] = float(av)
                else:
                    dictionary[ak] = int(av)
            except Exception as e:
                warnings.warn(f'Could not determine/convert type. Try to continue with type {type(av)} of {av}. '
                              f'Original error: {e}')
    return dictionary


def type2mongo(value: any) -> any:
    """Convert numpy dtypes to int/float/list/..."""
    if isinstance(value, (int, float, str, dict, datetime)):
        return value

    try:
        if np.issubdtype(value, np.floating):
            return float(value)
        else:
            return int(value)
    except Exception as e:
        warnings.warn(f'Could not determine/convert type. Try to continue with type {type(value)} of {value}. '
                      f'Original error: {e}')
    return value


@register_special_dataset('mongo', H5Group)
class MongoGroupAccessor:
    """Accessor for HDF5 datasets to Mongo DB"""

    def __init__(self, h5grp: H5Group):
        self._h5grp = h5grp

    def insert(self, collection: pymongo.collection.Collection, recursive: bool = False,
               include_dataset: bool = True,
               flatten_tree: bool = True,
               ignore_attrs: List[str] = None,
               ignore_upper_attr_name: bool = False) -> pymongo.collection.Collection:
        """Insert HDF group into collection"""

        if not flatten_tree:
            tree = self._h5grp.get_tree_structure(recursive=recursive,
                                                  ignore_attrs=ignore_attrs,
                                                  ignore_upper_attr_name=ignore_upper_attr_name)
            tree["file_creation_time"] = get_file_creation_time(self._h5grp.file.filename)
            # tree["document_last_modified"] = datetime.utcnow()  # last modified
            collection.insert_one(make_dict_mongo_compatible(tree))
            return collection

        if ignore_attrs is None:
            ignore_attrs = []

        grp = self._h5grp
        post = {"filename": str(grp.file.filename),
                "file_creation_time": get_file_creation_time(self._h5grp.file.filename),
                # "document_last_modified": datetime.utcnow(),  # last modified
                "path": grp.name, 'hdfobj': 'group'}

        for ak, av in grp.attrs.items():
            if ak not in ignore_attrs:
                if ignore_upper_attr_name:
                    if not ak.isupper():
                        post[ak] = type2mongo(av)
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
                    "file_creation_time": get_file_creation_time(self._h5ds.file.filename),
                    # "document_last_modified": datetime.now(),  # last modified
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
            for i in range(ds.shape[axis]):

                post = {"filename": str(ds.file.filename), "path": ds.name[1:],  # name without /
                        "file_creation_time": get_file_creation_time(self._h5ds.file.filename),
                        # "document_last_modified": datetime.utcnow(),  # last modified
                        "shape": ds.shape,
                        "ndim": ds.ndim,
                        'hdfobj': 'dataset',
                        'slice': ((i, i + 1, 1),
                                  (0, None, 1),
                                  (0, None, 1))}

                if len(ds.dims[axis]) > 0:
                    for iscale in range(len(ds.dims[axis])):
                        dim = ds.dims[axis][iscale]
                        if dim.ndim != 1:
                            warnings.warn(f'Dimension scale dataset must be 1D, not {dim.ndim}D. Skipping')
                            continue
                        scale = dim[i]
                        post[dim.name[1:]] = type2mongo(scale)

                for ak, av in ds.attrs.items():
                    if ak not in ignore_attrs:
                        if ak == 'COORDINATES':
                            if isinstance(av, (np.ndarray, list)):
                                for c in av:
                                    post[c[1:]] = float(ds.parent[c][()])
                            else:
                                post[av[1:]] = float(ds.parent[av][()])
                        else:
                            if not ak.isupper():
                                post[ak] = av
                collection.insert_one(post)
            return collection
        else:
            raise NotImplementedError('This method is under heavy construction. Currently, '
                                      'only accepts axis==0 in this developmet stage.')