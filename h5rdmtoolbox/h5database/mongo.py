import os
import pathlib
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

import h5py
import numpy as np
import pymongo.collection
from pymongo.errors import InvalidDocument

from .filequery import distinct
from ..h5wrapper import open_wrapper
from ..h5wrapper.accessory import register_special_dataset
from ..h5wrapper.h5file import H5Dataset, H5Group

H5_DIM_ATTRS = ('CLASS', 'NAME', 'DIMENSION_LIST', 'REFERENCE_LIST')


def get_file_creation_time(filename: str) -> datetime:
    """Return the creation time of the passed filename"""
    return datetime.fromtimestamp(pathlib.Path(filename).stat().st_ctime, tz=timezone.utc)


def make_dict_mongo_compatible(dictionary: Dict):
    """Make the values of a dictionary compatible with mongo DB"""
    for ak, av in dictionary.items():
        if isinstance(av, (int, float, str, list, tuple, datetime)):
            pass
        elif isinstance(av, dict):
            dictionary[ak] = make_dict_mongo_compatible(av)
        elif av is None:
            dictionary[ak] = None
        else:
            try:
                if np.issubdtype(av, np.floating):
                    dictionary[ak] = float(av)
                else:
                    dictionary[ak] = int(av)
            except Exception as e:
                warnings.warn(
                    f'Could not determine/convert type of {ak}. Try to continue with type {type(av)} of {av}. '
                    f'Original error: {e}')
    return dictionary


def type2mongo(value: any) -> any:
    """Convert numpy dtypes to int/float/list/..."""
    if isinstance(value, (int, float, str, dict, list, tuple, datetime)):
        return value
    elif value is None:
        return None
    try:
        if np.issubdtype(value, np.floating):
            return float(value)
        else:
            return int(value)
    except Exception as e:
        warnings.warn(f'Could not determine/convert {value}. Try to continue with type {type(value)} of {value}. '
                      f'Original error: {e}')
    return value


@register_special_dataset('mongo', H5Group)
class MongoGroupAccessor:
    """Accessor for HDF5 datasets to Mongo DB"""

    def __init__(self, h5grp: H5Group):
        self._h5grp = h5grp

    def insert(self, collection: pymongo.collection.Collection,
               recursive: bool = False,
               update: bool = True,
               include_dataset: bool = True,
               flatten_tree: bool = True,
               ignore_attrs: List[str] = None,
               use_relative_filename: bool = False,
               additional_fields: Dict = None) -> pymongo.collection.Collection:
        """Insert HDF group into collection"""

        filename_ctime = get_file_creation_time(self._h5grp.file.filename)
        if use_relative_filename:
            filename = self._h5grp.file.filename
        else:
            filename = str(pathlib.Path(self._h5grp.file.filename).absolute())

        if not flatten_tree:
            tree = self._h5grp.get_tree_structure(recursive=recursive,
                                                  ignore_attrs=ignore_attrs)
            tree["file_creation_time"] = filename_ctime
            tree["filename"] = filename
            try:
                collection.insert_one(make_dict_mongo_compatible(tree))
            except InvalidDocument as e:
                raise InvalidDocument(
                    f'Could not insert dict: \n{make_dict_mongo_compatible(tree)}\nOriginal error: {e}')
            return collection

        if ignore_attrs is None:
            ignore_attrs = []

        grp = self._h5grp
        doc = {"filename": str(filename),
               "file_creation_time": filename_ctime,
               "basename": os.path.basename(grp.name),
               "name": grp.name,
               'hdfobj': 'group'}

        if additional_fields is not None:
            doc.update(additional_fields)

        for ak, av in grp.attrs.items():
            if ak not in H5_DIM_ATTRS:
                if ak not in ignore_attrs:
                    doc[ak] = type2mongo(av)
        if update:
            collection.update_one(doc,
                                  {'$set': doc}, upsert=True)
        else:
            collection.insert_one(doc)

        if recursive:
            include_dataset = True

        if include_dataset or recursive:
            for dsname, h5obj in grp.items():
                if isinstance(h5obj, h5py.Dataset):
                    if include_dataset:
                        h5obj.mongo.insert(axis=None, collection=collection,
                                           update=update,
                                           ignore_attrs=ignore_attrs)
                else:
                    if recursive:
                        h5obj.mongo.insert(collection, recursive=recursive,
                                           update=update,
                                           include_dataset=include_dataset,
                                           ignore_attrs=ignore_attrs)
        return collection


@register_special_dataset('mongo', H5Dataset)
class MongoDatasetAccessor:
    """Accessor for HDF5 datasets to Mongo DB"""

    def __init__(self, h5ds: H5Dataset):
        self._h5ds = h5ds

    def get_documents(self, axis: int, ignore_attrs: List[str] = None, dims: List[str] = None,
                      use_relative_filename: bool = False,
                      use_standard_names_for_dimscales: bool = False) -> List[Dict]:
        """Generates the document from the dataset and return list of dictionaries"""
        if ignore_attrs is None:
            ignore_attrs = []

        ds = self._h5ds

        filename_ctime = get_file_creation_time(self._h5ds.file.filename)
        if use_relative_filename:
            filename = ds.file.filename
        else:
            filename = str(pathlib.Path(ds.file.filename).absolute())

        if axis is None:
            doc = {"filename": filename,
                   "name": ds.name,
                   "basename": os.path.basename(ds.name),
                   "file_creation_time": filename_ctime,
                   "shape": ds.shape,
                   "ndim": ds.ndim,
                   'hdfobj': 'dataset'}

            for ak, av in ds.attrs.items():
                if ak not in H5_DIM_ATTRS:
                    if ak not in ignore_attrs:
                        if ak == 'COORDINATES':
                            if isinstance(av, (np.ndarray, list)):
                                for c in av:
                                    doc[c] = float(ds.parent[c][()])
                            else:
                                doc[av] = float(ds.parent[av][()])
                        else:
                            doc[ak] = av
            return [doc, ]

        if axis == 0:
            docs = []
            for i in range(ds.shape[axis]):

                doc = {"filename": filename,
                       "name": ds.name,
                       "basename": os.path.basename(ds.name),
                       "file_creation_time": filename_ctime,
                       "shape": ds.shape,
                       "ndim": ds.ndim,
                       'hdfobj': 'dataset',
                       'slice': ((i, i + 1, 1),
                                 (0, None, 1),
                                 (0, None, 1))}

                dim_ls = []
                if dims is not None:
                    for dim in dims:
                        if not isinstance(dim, h5py.Dataset):
                            raise TypeError(f'Dimension must be of type h5py.Dataset, not {type(dim)}')
                        dim_ls.append(dim)

                if len(ds.dims[axis]) > 0:
                    for iscale in range(len(ds.dims[axis])):
                        dim = ds.dims[axis][iscale]
                        if dim.ndim != 1:
                            warnings.warn(f'Dimension scale dataset must be 1D, not {dim.ndim}D. Skipping')
                        else:
                            if dim.name not in dim_ls:
                                # add dim scale to list
                                dim_ls.append(dim)

                for dim in dim_ls:
                    scale = dim[i]
                    if use_standard_names_for_dimscales:
                        dimname_to_use = dim.attrs.get('standard_name')
                        if not dimname_to_use:
                            dimname_to_use = os.path.basename(dim.name[1:])
                        else:
                            if len(distinct(dim, 'standard_name', None)) > 1:
                                dimname_to_use = os.path.basename(dim.name[1:])
                                warnings.warn(f'Cannot use standard name of dim scale {dim.name} because it '
                                              f'is not distinct in the dataset')
                    else:
                        dimname_to_use = os.path.basename(dim.name[1:])
                    # TODO: add string entry that tells us where the scale ds is located
                    doc[dimname_to_use] = type2mongo(scale)

                for ak, av in ds.attrs.items():
                    if ak not in H5_DIM_ATTRS:
                        if ak not in ignore_attrs:
                            if ak == 'COORDINATES':
                                if isinstance(av, (np.ndarray, list)):
                                    for c in av:
                                        doc[c[1:]] = float(ds.parent[c][()])
                                else:
                                    doc[av[1:]] = float(ds.parent[av][()])
                            else:
                                doc[ak] = av
                docs.append(doc)
            return docs
        else:
            raise NotImplementedError('This method is under heavy construction. Currently, '
                                      'only accepts axis==0 in this developmet stage.')

    def insert(self, axis, collection: pymongo.collection.Collection,
               update: bool = True,
               ignore_attrs: List[str] = None, dims: List[str] = None,
               additional_fields: Dict = None, ordered: bool = True,
               use_standard_names_for_dimscales: bool = False) -> pymongo.collection.Collection:
        """Using axis is UNDER HEAVY CONSTRUCTION!!! Currently only axis=0 works

        By providing `dims` the dimension scales can be defined. If set to None, all attached
        scales are used
        """
        docs = self.get_documents(axis, ignore_attrs, dims,
                                  use_standard_names_for_dimscales=use_standard_names_for_dimscales)

        if additional_fields is not None:
            for doc in docs:
                doc.update(additional_fields)
        if update:
            for doc in docs:
                collection.update_one(doc, {'$set': doc}, upsert=True)
        else:
            collection.insert_many(docs, ordered=ordered)
        return collection

    def update(self, axis, collection: pymongo.collection.Collection,
               ignore_attrs: List[str] = None, dims: List[str] = None) -> pymongo.collection.Collection:
        """update the dataset content"""
        raise NotImplementedError('Planned to be implemented soon.')
        # docs = self.get_documents(axis, ignore_attrs, dims)
        # for doc in docs:
        #     myquery = doc
        #     newvalues = {"$set": doc}
        #     collection.update_one(myquery, newvalues)
        # return collection

    def slice(self, list_of_slices: List["slice"]) -> "xr.DataArray":
        """Slice the array with a mongo return value for a slice"""
        return self._h5ds[tuple([slice(*s) for s in list_of_slices])]


@dataclass
class H5Result:
    """Result interface. Either accessing a h5py.Dataset or a h5py.Group"""
    rdict: Dict

    def __post_init__(self):
        self.file = None

    # def dump(self):
    #     """Dump the content ofthe dataset/group to screen"""
    #     with self as h5:
    #         h5.dump()
    # def sdump(self):
    #     """Dump the content ofthe dataset/group to screen"""
    #     with self as h5:
    #         h5.sdump()
    def __getitem__(self, item):
        """Return sliced xarray for dataset. For group this will raise an error"""
        with self as h5:
            if isinstance(h5, h5py.Group):
                return h5.__getitem__(item)
            if 'slice' not in self.rdict:
                """return full array"""
                return h5[:]
            list_of_slices = self.rdict['slice']
            return h5[tuple([slice(*s) for s in list_of_slices])].__getitem__(item)

    def __enter__(self):
        if 'filename' not in self.rdict:
            raise AttributeError('No filename provided')
        return self.open()

    def open(self):
        """open the file"""
        try:
            self.file = open_wrapper(self.rdict['filename'])
        except RuntimeError as e:
            if self.file is not None:
                print('closing file')
                self.file.close()
            raise RuntimeError(e)
        return self.file[self.rdict['name']]

    def close(self):
        """close the file"""
        self.file.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


@dataclass
class H5Results:
    """Class interfacing a pymongo cursor that contains
    HDF5 entries build with this package"""

    cursor: pymongo.cursor.Cursor

    def __iter__(self):
        return self

    def __next__(self):
        return H5Result(self.cursor.next())

    def __getitem__(self, item) -> H5Result:
        if isinstance(item, int):
            for i, c in enumerate(self.cursor.rewind()):
                if i == item:
                    return H5Result(c)

    def rewind(self):
        """rewind the cursor"""
        self.cursor.rewind()
        return self

    def get(self, *names, fill_value=np.nan) -> Dict:
        """Get values of name(s) and return a dictionary"""
        dictionary = {n: [] for n in names}
        for c in self.cursor.rewind():
            for n in names:
                try:
                    dictionary[n].append(c[n])
                except IndexError:
                    dictionary[n].append(fill_value)
        return dictionary
