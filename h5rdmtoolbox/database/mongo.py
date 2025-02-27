import os
import pathlib
import warnings
from datetime import datetime
from typing import List, Dict, Any, Union, Generator

import h5py
import numpy as np
from pymongo.collection import Collection
from pymongo.errors import InvalidDocument

from .interface import ExtHDF5DBInterface
from .. import protected_attributes
from ..database import lazy


def get_file_creation_time(filename: Union[str, pathlib.Path], tz=None) -> datetime:
    """Return the creation time of the passed filename

    Parameters
    ----------
    filename : str or pathlib.Path
        The filename to get the creation time from
    tz : datetime.tzinfo, optional=None
        The timezone to use. If None, the local timezone is used.
        Default: None

    Returns
    -------
    datetime
        The creation time of the file
    """
    return datetime.fromtimestamp(pathlib.Path(filename).stat().st_ctime, tz=tz)


def make_dict_mongo_compatible(dictionary: Dict):
    """Make the values of a dictionary compatible with mongo DB"""
    for ak, av in dictionary.items():
        if isinstance(av, (int, float, str, list, tuple, datetime)):
            continue
        elif isinstance(av, dict):
            dictionary[ak] = make_dict_mongo_compatible(av)
        elif av is None:
            continue
        else:
            try:
                if np.issubdtype(av, np.floating):
                    dictionary[ak] = float(av)
                else:
                    dictionary[ak] = int(av)
            except Exception as e:
                warnings.warn(
                    f'Could not determine/convert type of {ak}. Try to continue with type {type(av)} of {av}. '
                    f'Original error: {e}',
                    UserWarning)
    return dictionary


def type2mongo(value: Any) -> Any:
    """Convert numpy dtypes to int/float/list/... At least try to convert to str()"""
    if isinstance(value, (int, float, str, dict, list, tuple, datetime)):
        return value
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        return value.tolist()
    try:
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        return str(value)
    except Exception as e:
        warnings.warn(f'Could not determine/convert {value}. Try to continue with type {type(value)} of {value}. '
                      f'Original error: {e}')
    return str(value)


def _generate_dataset_document(
        dataset: h5py.Dataset,
        axis: int,
        ignore_attrs: List[str] = None,
        dims: List[str] = None,
        use_relative_filename: bool = False,
        use_standard_names_for_dim_scales: bool = False
) -> List[Dict]:
    """Generate documents (dictionaries) for datasets to be inert into a mongoDB collection"""
    if ignore_attrs is None:
        ignore_attrs = []

    filename_ctime = get_file_creation_time(dataset.file.filename)
    if use_relative_filename:
        filename = dataset.file.filename
    else:
        filename = str(pathlib.Path(dataset.file.filename).absolute())

    # TODO improve readability of the the next lines
    if axis is None:
        doc = {"filename": filename,
               "name": dataset.name,
               "basename": os.path.basename(dataset.name),
               "file_creation_time": filename_ctime,
               "shape": dataset.shape,
               "ndim": dataset.ndim,
               'hdfobj': 'dataset'}

        if dataset.ndim == 0:
            doc['data'] = type2mongo(dataset[()])

        for ak, av in dataset.attrs.items():
            if ak not in protected_attributes.h5rdmtoolbox:
                if ak not in ignore_attrs:
                    # if ak == protected_attributes.COORDINATES:
                    #     if isinstance(av, (np.ndarray, list)):
                    #         for c in av:
                    #             doc[c] = float(dataset.parent[c][()])
                    #     else:
                    #         doc[av] = float(dataset.parent[av][()])
                    # else:
                    doc[ak] = type2mongo(av)
        return [doc, ]

    if axis == 0:
        docs = []
        for i in range(dataset.shape[axis]):

            doc = {"filename": filename,
                   "name": dataset.name,
                   "basename": os.path.basename(dataset.name),
                   "file_creation_time": filename_ctime,
                   "shape": dataset.shape,
                   "ndim": dataset.ndim,
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

            if len(dataset.dims[axis]) > 0:
                for iscale in range(len(dataset.dims[axis])):
                    dim = dataset.dims[axis][iscale]
                    if dim.ndim != 1:
                        warnings.warn(f'Dimension scale dataset must be 1D, not {dim.ndim}D. Skipping')
                    else:
                        if dim.name not in dim_ls:
                            # add dim scale to list
                            dim_ls.append(dim)

            for dim in dim_ls:
                scale = dim[i]
                if use_standard_names_for_dim_scales:
                    dim_name_to_use = dim.attrs.get('standard_name', None)
                    if dim_name_to_use is None:
                        dim_name_to_use = os.path.basename(dim.name[1:])

                else:
                    dim_name_to_use = os.path.basename(dim.name[1:])
                # TODO: add string entry that tells us where the scale ds is located
                doc[dim_name_to_use] = type2mongo(scale)

            for ak, av in dataset.attrs.items():
                if ak not in protected_attributes.h5rdmtoolbox:
                    if ak not in ignore_attrs:
                        if ak == protected_attributes.COORDINATES:
                            if isinstance(av, (np.ndarray, list)):
                                for c in av:
                                    doc[c[1:]] = float(dataset.parent[c][()])
                            else:
                                doc[av[1:]] = float(dataset.parent[av][()])
                        else:
                            doc[ak] = type2mongo(av)
            docs.append(doc)
        return docs
    raise NotImplementedError('This method is under heavy construction. Currently, '
                              'only accepts axis==0 in this development stage.')


def _insert_dataset(
        dataset: h5py.Dataset,
        collection: Collection,
        axis=None,
        update: bool = True,
        ignore_attrs: List[str] = None,
        dims: List[str] = None,
        additional_fields: Dict = None,
        ordered: bool = True,
        use_standard_names_for_dim_scales: bool = False):
    """Insert a dataset into the collection"""
    docs = _generate_dataset_document(
        dataset,
        axis,
        ignore_attrs,
        dims,
        use_standard_names_for_dim_scales=use_standard_names_for_dim_scales
    )

    if additional_fields is not None:
        for doc in docs:
            doc.update(additional_fields)
    if update:
        for doc in docs:
            _doc = {k: type2mongo(v) for k, v in doc.items()}
            collection.update_one(_doc, {'$set': _doc}, upsert=True)
    else:
        collection.insert_many(docs, ordered=ordered)
    return collection


def _insert_group(
        group: h5py.Group,
        collection: Collection,
        recursive: bool = False,
        update: bool = True,
        include_dataset: bool = True,
        flatten_tree: bool = True,
        ignore_attrs: List[str] = None,
        use_relative_filename: bool = False,
        additional_fields: Dict = None
):
    """Insert a group into the collection"""
    filename_ctime = get_file_creation_time(group.file.filename)
    if use_relative_filename:
        filename = group.file.filename
    else:
        filename = str(pathlib.Path(group.file.filename).absolute())

    if not flatten_tree:
        tree = group.get_tree_structure(recursive=recursive,
                                        ignore_attrs=ignore_attrs)
        tree["file_creation_time"] = filename_ctime
        tree["filename"] = filename
        try:
            collection.insert_one(make_dict_mongo_compatible(tree))
        except InvalidDocument as e:
            raise InvalidDocument(
                f'Could not insert dict: \n{make_dict_mongo_compatible(tree)}\nOriginal error: {e}') from e
        return collection

    if ignore_attrs is None:
        ignore_attrs = []

    grp = group
    doc = {"filename": str(filename),
           "file_creation_time": filename_ctime,
           "basename": os.path.basename(grp.name),
           "name": grp.name,
           'hdfobj': 'group'}

    if additional_fields is not None:
        doc.update(additional_fields)

    for ak, av in grp.attrs.items():
        if ak not in protected_attributes.h5rdmtoolbox:
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
        for h5obj in grp.values():
            if isinstance(h5obj, h5py.Dataset):
                if include_dataset:
                    _insert_dataset(h5obj, collection=collection,
                                    axis=None,
                                    update=update,
                                    ignore_attrs=ignore_attrs)
            else:
                if recursive:
                    _insert_group(h5obj, collection=collection, recursive=recursive,
                                  update=update,
                                  include_dataset=include_dataset,
                                  ignore_attrs=ignore_attrs)

    return collection


class MongoDBLazyDataset(lazy.LDataset):

    def __init__(self, obj: h5py.Dataset, mongo_doc):
        super().__init__(obj)
        self.__mongo_doc__ = mongo_doc

    def __getitem__(self, item):
        if 'slice' in self.__mongo_doc__:
            _slice = self.__mongo_doc__['slice']
            sliced_ds = super().__getitem__(tuple(slice(*s) for s in _slice))
            return sliced_ds.__getitem__(item)
        super().__getitem__(item)


class MongoDB(ExtHDF5DBInterface):
    """The database interface between HDF5 and MongoDB.

    Call `.insert()` on opened HDF5 files to insert them into the database.
    Call `.find_one()` or `.find()` to query the database. The syntax is the
    same as for pymongo. The returned objects are on-demand-opened HDF5 objects
    (see module `lazy`).
    """

    def __init__(self, collection: Collection):
        self.collection = collection

    def insert_dataset(self, dataset: h5py.Dataset, **kwargs):
        """Insert a dataset into the collection"""
        return _insert_dataset(dataset, self.collection, **kwargs)

    def insert_group(self, group: h5py.Group, **kwargs):
        """Insert a group into the collection"""
        return _insert_group(group, self.collection, **kwargs)

    def find_one(self, *args, **kwargs) -> lazy.LHDFObject:
        """Calls the `.find_one` method of the underlying pymongo collection.
        If the result contains data either the corresponding lazy (on-demand)
        dataset or group is returned."""
        res = self.collection.find_one(*args, **kwargs)
        if res:
            if 'filename' not in res:
                raise KeyError('No filename in result. This could mean, that the '
                               'database was not written with the toolbox. You might '
                               'want to add {"filename": {"$exists": True}} to your query '
                               'to ensure that the key is included or perform the query '
                               'with the original pymongo package, which will return the '
                               'plain dictionary object.')

            with h5py.File(res['filename'], 'r') as h5:
                if 'slice' in res:
                    return MongoDBLazyDataset(h5[res['name']], res)
                return lazy.lazy(h5[res['name']])

    def find(self, *args, **kwargs) -> Generator[lazy.LHDFObject, None, None]:
        """Calls the `.find` method of the underlying pymongo collection.
        If the result contains data either the corresponding lazy (on-demand)
        dataset or group is returned. Note, that the returned objects are
        generators, which need to be iterated over to get the actual data.

        Parameters
        ----------
        *args
            Positional arguments passed to the pymongo collection.
        **kwargs
            Keyword arguments passed to the pymongo collection.

        Yields
        ------
        lazy.LHDFObject
            The lazy (on-demand) dataset or group.
        """
        results = self.collection.find(*args, **kwargs)

        for res in results:
            if 'filename' not in res:
                raise KeyError('No filename in result. This could mean, that the '
                               'database was not written with the toolbox. You might '
                               'want to add {"filename": {"$exists": True}} to your query '
                               'to ensure that the key is included or perform the query '
                               'with the original pymongo package, which will return the '
                               'plain dictionary object.')
            with h5py.File(res['filename'], 'r') as h5:
                if 'slice' in res:
                    yield MongoDBLazyDataset(h5[res['name']], res)
                else:
                    yield lazy.lazy(h5[res['name']])
