"""Core wrapper module containing basic wrapper implementation of H5File, H5Dataset and H5Group
"""
import datetime
import h5py
import logging
import numpy as np
import os
import pathlib
# noinspection PyUnresolvedReferences
import pint_xarray
import shutil
import warnings
import xarray as xr
import yaml
from datetime import datetime, timezone
from h5py._hl.base import phil
from h5py._objects import ObjectID
from pathlib import Path
from pint_xarray import unit_registry as ureg
from tqdm import tqdm
from typing import List, Dict, Union, Tuple

# noinspection PyUnresolvedReferences
from . import xr2hdf
from .h5attr import H5_DIM_ATTRS, pop_hdf_attributes
from .h5attr import WrapperAttributeManager
from .h5utils import _is_not_valid_natural_name, get_rootparent
from .. import _repr
from .. import utils
from .._repr import H5Repr, H5PY_SPECIAL_ATTRIBUTES
from .._user import user_dirs
from .._version import __version__
from ..config import CONFIG
from ..conventions.layout import H5Layout

logger = logging.getLogger(__package__)

MODIFIABLE_PROPERTIES_OF_A_DATASET = ('name', 'chunks', 'compression', 'compression_opts',
                                      'dtype', 'maxshape')
ureg.default_format = CONFIG.UREG_FORMAT

H5File_layout_filename = Path.joinpath(user_dirs['layouts'], 'H5File.hdf')
if not H5File_layout_filename.exists():
    shutil.copy2(pathlib.Path(__file__).parent / '../data/H5File.hdf', H5File_layout_filename)


class Lower(str):
    """Lower"""

    def __new__(cls, string):
        instance = super().__new__(cls, string.lower())
        return instance


def lower(string: str) -> Lower:
    """return object Lower(string). Used when a dataset
    is called, but the upper/lower case should be irrelevant."""
    return Lower(string)


class H5Group(h5py.Group):
    """Inherited Group of the package h5py
    """
    convention = 'default'
    hdfrepr = H5Repr()

    @property
    def attrs(self):
        """Calls the wrapper attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    @property
    def rootparent(self):
        """Return the root group instance."""
        if self.name == '/':
            return self
        return get_rootparent(self.parent)

    @property
    def basename(self) -> str:
        """Basename of dataset (path without leading forward slash)"""
        return os.path.basename(self.name)

    def get_datasets(self, pattern=None) -> List[h5py.Dataset]:
        """Return list of datasets in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the datasets."""
        dsets = [v for k, v in self.items() if isinstance(v, h5py.Dataset)]
        if pattern is None:
            return dsets
        import re
        return [ds for ds in dsets if re.search(pattern, os.path.basename(ds.name))]

    def get_groups(self, pattern: str = '.*', rec: bool = False) -> List[h5py.Group]:
        """Return list of groups in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the groups."""
        if pattern == '.*' and not rec:
            return [v for v in self.values() if isinstance(v, h5py.Group)]
        return self.find({'$basename': {'$regex': pattern}}, rec=rec)

    def modify_dataset_properties(self, dataset, **dataset_properties):
        """Modify properties of a dataset that requires to outsource the dataset (copy to tmp file)
        and then copy it back with the new properties. 'static' properties are considered properties
        that cannot be changed once the dataset has been written, such as max_shape, dtype etc."""
        if not isinstance(dataset_properties, dict):
            raise TypeError(f'Expecting type dict for "properties" but got {type(dataset_properties)}')
        for k in dataset_properties.keys():
            if k not in MODIFIABLE_PROPERTIES_OF_A_DATASET:
                raise KeyError(f'Property "{k}" not in list of modifiable properties: '
                               f'{MODIFIABLE_PROPERTIES_OF_A_DATASET}')

        dataset_basename = dataset.basename

        name = dataset_properties.get('name', dataset_basename)
        if name != dataset_basename and name in self:
            raise KeyError('Renaming the dataset is not possible because new name already exists in group'
                           f' {self.name}')

        # get properties or source dataset
        _orig_dataset_properties = {k: dataset.__getattr__(k) for k in MODIFIABLE_PROPERTIES_OF_A_DATASET}
        worth_changing = False
        for k, v in dataset_properties.items():
            if v != _orig_dataset_properties[k]:
                worth_changing = True
                _orig_dataset_properties.update({k: v})

        if not worth_changing:
            warnings.warn(f'No changes were applied because new properties a no different to present ones', UserWarning)
            return dataset

        with H5File() as temp_h5dest:
            self.copy(dataset_basename, temp_h5dest)
            tmp_ds = temp_h5dest[dataset_basename]

            # delete dataset from this file
            del self[dataset_basename]

            attrs = dict(tmp_ds.attrs.items())
            # create new dataset with same name but different chunks:
            new_ds = self.create_dataset(name=_orig_dataset_properties.pop('name'),
                                         shape=tmp_ds.shape,
                                         attrs=attrs,
                                         **_orig_dataset_properties)

            # copy the data chunk-wise
            for chunk_slice in tmp_ds.iter_chunks():
                new_ds.values[chunk_slice] = tmp_ds.values[chunk_slice]

        return new_ds

    def __init__(self, _id):
        if isinstance(_id, h5py.Group):
            _id = _id.id
        if isinstance(_id, h5py.h5g.GroupID):
            super().__init__(_id)
        else:
            ValueError('Could not initialize Group. A h5py.h5f.FileID object must be passed')

    def __setitem__(self,
                    name: str,
                    obj: Union[xr.DataArray, List, Tuple, Dict]) -> None:
        """
        Lazy creating datasets. More difficult than using h5py as mandatory
        parameters must be provided.

        Parameters
        ----------
        name: str
            Name of dataset
        obj: xr.DataArray or Dict or List/Tuple of data and meta data-
            If obj is not a xr.DataArray, data must be provided using a list or tuple.
            See examples for possible ways to pass data.

        Returns
        -------
        None
        """
        if isinstance(obj, xr.DataArray):
            _ = obj.hdf.to_group(H5Group(self), name)
        elif isinstance(obj, (list, tuple)):
            if not isinstance(obj[1], dict):
                raise TypeError(f'Second item must be type dict but is {type(obj[1])}')
            kwargs = obj[1]
            self.create_dataset(name, data=obj[0], **kwargs)
        elif isinstance(obj, dict):
            self.create_dataset(**obj)
        else:
            super().__setitem__(name, obj)

    def __getitem__(self, name):
        if isinstance(name, Lower):
            for k in self.keys():
                if name == k.lower():
                    name = k
                    break
        ret = super().__getitem__(name)
        if isinstance(ret, h5py.Dataset):
            return self._h5ds(ret.id)
        elif isinstance(ret, h5py.Group):
            return self._h5grp(ret.id)
        return ret

    def __getattr__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError as e:
            if CONFIG.NATURAL_NAMING:
                pass
            else:
                raise AttributeError(e)

        if item in self.__dict__:
            return super().__getattribute__(item)
        try:
            if item in self:
                if isinstance(self[item], h5py.Group):
                    return self._h5grp(self[item].id)
                else:
                    return self._h5ds(self[item].id)
            else:
                # try replacing underscores with spaces:
                _item = item.replace('_', ' ')
                if _item in self:
                    if isinstance(self[_item], h5py.Group):
                        return self.__class__(self[_item].id)
                    else:
                        return self._h5ds(self[_item].id)
                else:
                    return super().__getattribute__(item)
        except AttributeError:
            raise AttributeError(item)

    def __str__(self) -> str:
        return f'<HDF5 wrapper group "{self.name}" (members: {len(self)}, convention: "{self.convention}")>'

    def __repr__(self) -> str:
        return self.__str__()

    def __lt__(self, other):
        return self.name < other.name

    def get_tree_structure(self, recursive=True, ignore_attrs: List[str] = None):
        """Return the tree (attributes, names, shapes) of the group and subgroups"""
        if ignore_attrs is None:
            ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        tree = {ak: av for ak, av in self.attrs.items()}
        for k, v in self.items():
            if isinstance(v, h5py.Dataset):
                ds_dict = {'shape': v.shape, 'ndim': v.ndim}
                for ak, av in v.attrs.items():
                    if ak not in H5_DIM_ATTRS:
                        if ak not in ignore_attrs:
                            ds_dict[ak] = av
                tree[k] = ds_dict
            else:
                if recursive:
                    tree[k] = v.get_tree_structure(recursive)
        return tree

    def create_group(self,
                     name: str,
                     overwrite: bool = None,
                     attrs: Dict = None,
                     *,
                     update_attrs: bool = False,
                     track_order=None):
        """
        Overwrites parent methods. Additional parameters are "long_name" and "attrs".
        Besides, it does and behaves the same. Differently to dataset creating
        long_name is not mandatory (i.e. will not raise a warning).

        Parameters
        ----------
        name : str
            Name of group
        overwrite : bool, default=None
            If the group does not already exist, the new group is written and this parameter has no effect.
            If the group exists and ...
            ... overwrite is None: h5py behaviour is enabled meaning that if a group exists h5py will raise
            ... overwrite is True: group is deleted and rewritten according to method parameters
            ... overwrite is False: group creation has no effect. Existing group is returned.
        attrs : dict, optional
            Attributes of the group, default is None which is an empty dict
        track_order : bool or None
            Track creation order under this group. Default is None.
        """
        if name in self:
            if name in self:
                if isinstance(self[name], h5py.Group):
                    if overwrite is True:
                        del self[name]
                    elif update_attrs:
                        g = self[name]
                        for ak, av in attrs.items():
                            g.attrs[ak] = av
                        return g
                    else:
                        # let h5py.Group raise the error...
                        h5py.Group.create_group(self, name, track_order=track_order)
                else:  # isinstance(self[name], h5py.Dataset):
                    raise RuntimeError('The name you passed is already ued for a dataset!')

        if _is_not_valid_natural_name(self, name, CONFIG.NATURAL_NAMING):
            raise ValueError(f'The group name "{name}" is not valid. It is an '
                             f'attribute of the class and cannot be used '
                             f'while natural naming is enabled')

        subgrp = super().create_group(name, track_order=track_order)

        # new_subgroup = h5py.Group.create_group(self, name, track_order=track_order)
        logger.debug(f'Created group "{name}" at "{self.name}"-level.')

        if attrs:
            for k, v in attrs.items():
                subgrp.attrs[k] = v

        return self._h5grp(subgrp)

    def create_string_dataset(self,
                              name: str,
                              data: Union[str, List[str]],
                              overwrite=False,
                              attrs=None):
        """Create a string dataset. In this version only one string is allowed.
        In future version a list of strings may be allowed, too.
        No long or standard name needed"""
        if isinstance(data, str):
            n_letter = len(data)
        elif isinstance(data, (tuple, list)):
            n_letter = max([len(d) for d in data])
        else:
            raise TypeError(f'Unexpected type for parameter "data": {type(data)}. Expected str or List/Tuple of str')
        dtype = f'S{n_letter}'
        if name in self:
            if overwrite is True:
                del self[name]  # delete existing dataset
            # else let h5py return the error
        ds = super().create_dataset(name, dtype=dtype, data=data)
        if attrs is None:
            attrs = {}
        for ak, av in attrs.items():
            ds.attrs[ak] = av
        # TODO: H5StingDataset
        return ds

    def create_dataset(self,
                       name,
                       shape=None,
                       dtype=None,
                       data=None,
                       overwrite=None,
                       chunks=True,
                       attrs=None,
                       attach_scales=None,
                       make_scale=False,
                       **kwargs):
        """
        Creating a dataset. Allows attaching/making scale, overwriting and setting attributes simultaneously.

        Parameters
        ----------
        name : str
            Name of dataset
        shape : tuple, optional
            Dataset shape. see h5py doc. Default None. Required if data=None.
        dtype : str, optional
            dtype of dataset. see h5py doc. Default is dtype('f')
        data : numpy ndarray, default=None
            Provide data to initialize the dataset.  If not used,
            provide shape and optionally dtype via kwargs (see more in
            h5py documentation regarding arguments for create_dataset
        overwrite : bool, default=None
            If the dataset does not already exist, the new dataset is written and this parameter has no effect.
            If the dataset exists and ...
            ... overwrite is None: h5py behaviour is enabled meaning that if a dataset exists h5py will raise
            ... overwrite is True: dataset is deleted and rewritten according to method parameters
            ... overwrite is False: dataset creation has no effect. Existing dataset is returned.
        chunks : bool or according to h5py.File.create_dataset documentation
            Needs to be True if later resizing is planned
        attrs : dict, optional
            Allows to set attributes directly after dataset creation. Default is
            None, which is an empty dict
        attach_scales : tuple, optional
            Tuple defining the datasets to attach scales to. Content of tuples are
            internal hdf paths. If an axis should not be attached to any axis leave it
            empty (''). Default is ('',) which attaches no scales
            Note: internal hdf5 path is relative w.r.t. this dataset, so be careful
            where to create the dataset and to which to attach the scales!
            Also note, that if data is a xr.DataArray and attach_scales is not None,
            coordinates of xr.DataArray are ignored and only attach_scales is
            considered.
        make_scale: bool, default=False
            Makes this dataset scale. The parameter attach_scale must be uses, thus be None.
        **kwargs
            see documentation of h5py.File.create_dataset

        Returns
        -------
        ds : h5py.Dataset
            created dataset
        """
        if isinstance(data, str):
            return self.create_string_dataset(name=name,
                                              data=data,
                                              overwrite=overwrite,
                                              attrs=attrs, **kwargs)
        if attrs is None:
            attrs = {}
        else:
            if isinstance(data, xr.DataArray):
                data.attrs.update(attrs)

        if name:
            if name in self:
                if overwrite is True:
                    del self[name]  # delete existing dataset
                elif overwrite is False:
                    return self[name]  # return existing dataset
                else:
                    # let h5py run into the error...
                    super().create_dataset(name, shape, dtype, data, **kwargs)

        # take compression from kwargs or config:
        compression = kwargs.pop('compression', CONFIG.HDF_COMPRESSION)
        compression_opts = kwargs.pop('compression_opts', CONFIG.HDF_COMPRESSION_OPTS)
        if shape is not None:
            if len(shape) == 0:
                compression, compression_opts, chunks = None, None, None

        if attrs is None:
            attrs = {}

        if isinstance(data, xr.DataArray):
            attrs.update(data.attrs)

            dset = data.hdf.to_group(H5Group(self), name=name, overwrite=overwrite,
                                     compression=compression,
                                     compression_opts=compression_opts, attrs=attrs)
            return dset

        if not isinstance(make_scale, (bool, str)):
            raise TypeError(f'Make scale must be a boolean or a string not {type(make_scale)}')

        if attach_scales is None:
            # maybe there's a typo:
            attach_scales = kwargs.pop('attach_scale', None)

        if name:
            if _is_not_valid_natural_name(self, name, CONFIG.NATURAL_NAMING):
                raise ValueError(f'The dataset name "{name}" is not a valid. It is an '
                                 f'attribute of the class and cannot be used '
                                 f'while natural naming is enabled')

        if isinstance(shape, np.ndarray):  # need if no keyword is used
            data = shape
            shape = None

        if data is not None:
            _data = np.asarray(data)
        else:
            _data = data

        _maxshape = kwargs.get('maxshape', shape)

        if attach_scales:
            if not isinstance(attach_scales, (list, tuple)):
                attach_scales = (attach_scales,)
            if any([True for a in attach_scales if a]) and make_scale:
                raise ValueError(
                    'Cannot make scale and attach scale at the same time!')

        logger.debug(
            f'Creating H5DatasetModel "{name}" in "{self.name}" with maxshape {_maxshape} " '
            f'and using compression "{compression}" with opt "{compression_opts}"')

        if _data is not None:
            if _data.ndim == 0:
                _ds = super().create_dataset(name,
                                             shape=shape,
                                             dtype=dtype,
                                             data=_data,
                                             **kwargs)
            else:
                _ds = super().create_dataset(name,
                                             shape=shape,
                                             dtype=dtype,
                                             data=_data,
                                             chunks=chunks,
                                             compression=compression,
                                             compression_opts=compression_opts,
                                             **kwargs)
        else:
            _ds = super().create_dataset(name, shape=shape, dtype=dtype, data=_data,
                                         compression=compression,
                                         compression_opts=compression_opts,
                                         chunks=chunks,
                                         **kwargs)

        ds = self._h5ds(_ds.id)

        if attrs:
            for k, v in attrs.items():
                ds.attrs[k] = v

        # make scale
        if make_scale:
            if isinstance(make_scale, bool):
                ds.make_scale('')
            elif isinstance(make_scale, str):
                ds.make_scale(make_scale)
            else:
                raise TypeError('Parameter "make_scale" must be a string.')

        # attach scales:
        if attach_scales:
            for i, s in enumerate(attach_scales):
                if s:
                    if not isinstance(s, (tuple, list)):
                        _s = (s,)
                    else:
                        _s = s
                    for ss in _s:
                        if isinstance(ss, h5py.Dataset):
                            ds.dims[i].attach_scale(ss)
                        else:
                            if ss in self:
                                ds.dims[i].attach_scale(self[ss])
                            else:
                                raise ValueError(f'Cannot assign {ss} to {ds.name} because it seems not '
                                                 f'to exist!')

        return self._h5ds(ds.id)

    def find_one(self, flt: Union[Dict, str],
                 objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
                 rec: bool = True):
        """See find()"""
        from ..database import filequery
        objfilter = utils.process_obj_filter_input(objfilter)
        return filequery.find(
            self,
            flt,
            objfilter=objfilter,
            recursive=rec,
            find_one=True
        )

    def distinct(self,
                 key,
                 objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None
                 ) -> List:
        """Find a distinct key"""
        from ..database.filequery import distinct
        objfilter = utils.process_obj_filter_input(objfilter)
        return distinct(self, key, objfilter)

    def find(self, flt: Union[Dict, str],
             objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
             rec: bool = True):
        """
        Examples for filter parameters:
        filter = {'long_name': 'any objects long name'} --> searches in attributes only
        filter = {'$name': 'name'}  --> searches in groups and datasets for the (path)name
        filter = {'basename': 'name'}  --> searches in groups and datasets for the basename (without path)

        Parameters
        ----------
        flt: Dict
            Filter request
        objfilter: str | h5py.Dataset | h5py.Group | None
            Filter. Default is None. Otherwise, only dataset or group types are returned.
        rec: bool, optional
            Recursive search. Default is True

        Returns
        -------
        h5obj: h5py.Dataset or h5py.Group
        """
        from ..database import filequery
        objfilter = utils.process_obj_filter_input(objfilter)
        return filequery.find(
            h5obj=self,
            flt=flt,
            objfilter=objfilter,
            recursive=rec,
            find_one=False)

    def create_datasets_from_csv(self,
                                 csv_filename,
                                 dim_column: Union[int, str] = 0,
                                 shape=None,
                                 overwrite=False,
                                 combine_opt='stack',
                                 axis=0, chunks=None,
                                 attrs: Dict = None,
                                 **pandas_kwargs):
        """
        Reads data from a csv and adds a dataset according to column names.
        Pandas.read_csv() is used. So all arguments for this function may be passed.

        Parameters
        ----------
        csv_filename : Path or list of Path
            CSV filename or list of filenames.
            If list is passed, structure must be the same for all
        dim_column : Union[int, str], optional=0
            The column index or name to be used as dimension. All other
            datasets get this dimension attached as coordinate.
        shape : tuple
            Target shape of data. Default is None.
            As data is column data. it can be reshaped to desired shape.
        overwrite : bool
            Whether to overwrite an existing dataset. Default is False.
        combine_opt : str
            Defines the method how to combine data from multiple files.
            Therefore, csv_filename must be a list. Default is stack.
            If set, make sure, axis is set accordingly.
            Other input can be concatenated
        axis : int
            Stacking or concatenating according to combine_opt along
            if multiple csv files are passes
        chunks : tuple
            Chunking option for HDF5 dataset creation. Equal for all
            datasets
        attrs : Dict
            Dictionary containing attributes for the columns. The keys
            must match the column names of the csv.

        Returns
        -------
        None

        """
        from pandas import read_csv as pd_read_csv
        if attrs is None:
            attrs = {}
        if 'names' in pandas_kwargs.keys():
            if 'header' not in pandas_kwargs.keys():
                raise RuntimeError('if you pass names also pass header=...')

        if isinstance(csv_filename, (list, tuple)):
            # depending on the meaning of multiple csv_filename axis can be 0 (z-plane)
            # or 1 (time-plane)
            axis = pandas_kwargs.pop('axis', 0)
            csv_fname = csv_filename[0]
            is_single_file = False
        elif isinstance(csv_filename, (str, Path)):
            is_single_file = True
            csv_fname = csv_filename
        else:
            raise ValueError(
                f'Wrong input for "csv_filename: {type(csv_filename)}')

        df = pd_read_csv(csv_fname, **pandas_kwargs)

        compression, compression_opts = CONFIG.HDF_COMPRESSION, CONFIG.HDF_COMPRESSION_OPTS

        if is_single_file:
            for variable_name in df.columns:
                ds_name = utils.remove_special_chars(str(variable_name))
                data = df[str(variable_name)].values.reshape(shape)
                try:
                    self.create_dataset(name=ds_name,
                                        data=data,
                                        attrs=attrs.get(ds_name, None),
                                        overwrite=overwrite, compression=compression,
                                        compression_opts=compression_opts)
                except RuntimeError as e:
                    logger.error(
                        f'Could not read {variable_name} from csv file due to: {e}')
        else:
            _data = df[df.columns[0]].values.reshape(shape)
            nfiles = len(csv_filename)
            for variable_name in df.columns:
                ds_name = utils.remove_special_chars(str(variable_name))
                if combine_opt == 'concatenate':
                    _shape = list(_data.shape)
                    _shape[axis] = nfiles
                    self.create_dataset(name=ds_name, shape=_shape,
                                        attrs=attrs.get(ds_name, None),
                                        compression=compression,
                                        compression_opts=compression_opts,
                                        chunks=chunks)
                elif combine_opt == 'stack':
                    if axis == 0:
                        self.create_dataset(name=ds_name, shape=(nfiles, *_data.shape),
                                            attrs=attrs.get(ds_name, None),
                                            compression=compression,
                                            compression_opts=compression_opts,
                                            chunks=chunks)
                    elif axis == 1:
                        self.create_dataset(name=ds_name, shape=(_data.shape[0], nfiles, *_data.shape[1:]),
                                            attrs=attrs.get(ds_name, None),
                                            compression=compression,
                                            compression_opts=compression_opts,
                                            chunks=chunks)
                    else:
                        raise ValueError('axis must be 0 or -1')

                else:
                    raise ValueError(
                        f'"combine_opt" must be "concatenate" or "stack", not {combine_opt}')

            for i, csv_fname in enumerate(csv_filename):
                df = pd_read_csv(csv_fname, **pandas_kwargs)
                for c in df.columns:
                    ds_name = utils.remove_special_chars(str(c))
                    data = df[str(c)].values.reshape(shape)

                    if combine_opt == 'concatenate':
                        if axis == 0:
                            self[ds_name][i, ...] = data[0, ...]
                        elif axis == 1:
                            self[ds_name][:, i, ...] = data[0, ...]
                    elif combine_opt == 'stack':
                        if axis == 0:
                            self[ds_name][i, ...] = data
                        elif axis == 1:
                            self[ds_name][:, i, ...] = data

    def create_dataset_from_image(self, img_filename, name=None,
                                  overwrite=False, dtype=None, ufunc=None,
                                  axis=0, **kwargs):
        """
        Creates a dataset for a single or multiple files. If a list of filenames is passed
        All images are stacked (thus shape of all images must be equal!)

        Parameters
        ----------
        img_filename : {Path, list}
            Image filename or list of image file names. See also axis in case of multiple files
        name : str
            Name of create dataset
        units : string
            Unit of image. Typically, pixels which is also default.
        long_name : str
            long_name of dataset
        overwrite : bool
            Whether to overwrite an existing dataset with this name
        dtype : str
            Data type used for hdf dataset creation
        axis: int, optional
            Axis along which to stack images in case of multiple ones.
            Valid axis values are either 0 or -1.
            Default is 0.

        Returns
        -------
        ds : hdf Dataset
            The created dataset.

        """

        # take compression from kwargs or config:
        _compression, _compression_opts = CONFIG.HDF_COMPRESSION, CONFIG.HDF_COMPRESSION_OPTS
        compression = kwargs.pop('compression', _compression)
        compression_opts = kwargs.pop('compression_opts', _compression_opts)
        units = kwargs.pop('units', 'pixel')
        ds = None

        if isinstance(img_filename, (str, Path)):
            if name is None:
                name = utils.remove_special_chars(
                    os.path.basename(img_filename).rsplit('.', 1)[0])
            img = utils.load_img(img_filename)
            if ufunc is not None:
                if isinstance(ufunc, (list, tuple)):
                    _ufunc = ufunc[0]
                    _ufunc_param = ufunc[1:]
                    raise NotImplementedError(
                        'user function with parameter not implemented yet')
                elif hasattr(ufunc, '__call__'):
                    try:
                        img_processed = ufunc(img)
                    except RuntimeError as e:
                        raise logger.error(f'Failed running user function {ufunc} '
                                           f'with this error: {e}')
                    if img_processed is not None:
                        ds = self.create_dataset(name=name, data=img_processed,
                                                 overwrite=overwrite,
                                                 dtype=dtype, compression=compression,
                                                 compression_opts=compression_opts,
                                                 units=units,
                                                 **kwargs)
                        return ds

            else:
                ds = self.create_dataset(name=name, data=img,
                                         overwrite=overwrite, dtype=dtype,
                                         compression=compression, compression_opts=compression_opts)
                return ds
        elif isinstance(img_filename, (list, tuple)):
            if not name:  # take the first image name
                name = os.path.commonprefix(img_filename)
            nimg = len(img_filename)

            if ufunc is not None:  # user function given. final size of dataset unknown
                if isinstance(ufunc, (list, tuple)):
                    _ufunc = ufunc[0]
                    _ufunc_param = ufunc[1:]
                    # raise NotImplementedError('user function with parameter not implemented yet')
                else:
                    _ufunc = ufunc
                    _ufunc_param = list()

                if hasattr(_ufunc, '__call__'):
                    for i, img_fname in tqdm(enumerate(img_filename)):
                        img = utils.load_img(img_fname)
                        img_shape = img.shape
                        try:
                            if hasattr(ufunc, '__call__'):
                                img_processed = _ufunc(img)
                            else:
                                img_processed = _ufunc(img, *_ufunc_param)
                        except RuntimeError as e:
                            raise logger.error(f'Failed running user function {_ufunc} '
                                               f'with this error: {e}')
                        if img_processed is not None:
                            if name in self:  # dataset already exists
                                ds = self[name]
                                ds_shape = list(ds.shape)
                                if axis == 0:
                                    ds_shape[0] += 1
                                else:
                                    ds_shape[-1] += 1
                                ds.resize(tuple(ds_shape))
                                if axis == 0:
                                    ds[-1, ...] = img_processed
                                else:
                                    ds[..., -1] = img_processed
                            else:  # dataset must be created first
                                if axis == 0:
                                    dataset_shape = (1, *img_shape)
                                    _maxshape = (None, *img_shape)
                                    _chunks = (1, *img_shape)
                                elif axis == -1:
                                    dataset_shape = (*img_shape, 1)
                                    _maxshape = (*img_shape, None)
                                    _chunks = (*img_shape, 1)
                                else:
                                    raise ValueError('Other axis than 0 or -1 not accepted!')
                                ds = self.create_dataset(name, shape=dataset_shape, overwrite=overwrite,
                                                         maxshape=_maxshape, dtype=dtype, compression=compression,
                                                         compression_opts=compression_opts, chunks=_chunks)
                                if axis == 0:
                                    ds[0, ...] = img
                                else:
                                    ds[..., 0] = img
                else:
                    raise ValueError(f'Wrong ufunc type: {type(ufunc)}')
                return ds
            else:  # no user function passed. shape of dataset is known and can be pre-allocated
                img = utils.load_img(img_filename[0])
                img_shape = img.shape
                if axis == 0:
                    dataset_shape = (nimg, *img_shape)
                elif axis == -1:
                    dataset_shape = (*img_shape, nimg)
                else:
                    raise ValueError('Other axis than 0 or -1 not accepted!')

                # pre-allocate dataset with shape:
                ds = self.create_dataset(name, shape=dataset_shape, overwrite=overwrite,
                                         dtype=dtype, compression=compression, compression_opts=compression_opts)

                # fill dataset with data:
                if ds is not None:
                    if axis == 0:
                        ds[0, ...] = img
                        for i, img_fname in tqdm(enumerate(img_filename[1:]), unit='file', desc='processing images'):
                            img = utils.load_img(img_fname)
                            if img.shape == img_shape:
                                ds[i + 1, ...] = img
                            else:
                                logger.critical(
                                    f'Shape of {img_fname} has wrong shape {img.shape}. Expected shape: {img_shape}'
                                    ' Dataset will be deleted again!'
                                )
                                del self[ds.name]
                    elif axis == -1:
                        ds[..., 0] = img
                        for i, img_fname in tqdm(enumerate(img_filename[1:]), unit='file', desc='processing images'):
                            img = utils.load_img(img_filename[0])
                            if img.shape == img_shape:
                                ds[..., i + 1] = img
                            else:
                                logger.critical(
                                    f'Shape if {img_fname} has wrong shape {img.shape}. Expected shape: {img_shape}'
                                    f' Dataset will be deleted again!')
                                del self[ds.name]
                    return ds
                else:
                    logger.critical(
                        'Could not create dataset because it already exists and overwrite=False.')

    def create_dataset_from_xarray_dataset(self, dataset: xr.Dataset) -> None:
        """creates the xr.DataArrays of the passed xr.Dataset, writes all attributes
        and handles the dimension scales."""
        ds_coords = {}
        for coord in dataset.coords.keys():
            ds = self.create_dataset(coord,
                                     data=dataset.coords[coord].values,
                                     attrs=dataset.coords[coord].attrs,
                                     overwrite=False)
            ds.make_scale()
            ds_coords[coord] = ds
        for data_var in dataset.data_vars.keys():
            ds = self.create_dataset(data_var,
                                     data=dataset[data_var].values,
                                     attrs=dataset[data_var].attrs,
                                     overwrite=False)
            for idim, dim in enumerate(dataset[data_var].dims):
                if dim not in ds_coords:
                    # xarray does not let me add attributes to this dimension
                    h5py.Group(self.id).create_dataset(name=dim, data=dataset[data_var][dim].values)
                    ds_coords[dim] = ds
                else:
                    ds.dims[idim].attach_scale(ds_coords[dim])

    def create_external_link(self, name, filename, path, overwrite=False,
                             keep_relative=False):
        """
        Creates a group which points to group in another file. See h5py.ExternalLink()
        for more information.

        Parameters
        ----------
        name : str
            Group name that is created in this hdf file
        filename : Path
            File name of remote HDF5 file
        path : Path
            HDF5 internal path to group that should be linked to
        overwrite : bool, optional
            Whether to overwrite an existing dataset. Default is False.
        keep_relative : bool, optional
            If true, path is untouched. If False, os.path.abspath() is applied.
        """
        logger.debug(f'Trying to create external link group with name "{name}". Source is filename="{filename}" and '
                     f'path="{path}". Overwrite is set to {overwrite} and keep_relative to {keep_relative}')
        if not keep_relative:
            filename = os.path.abspath(filename)
        if name in self:
            if overwrite:
                del self[name]
                self[name] = h5py.ExternalLink(filename, path)
                return self[name]
            else:
                logger.debug('External link %s was not created. A Dataset with this name'
                             ' already exists and overwrite is set to False! '
                             'You can pass overwrite=True in order to overwrite the '
                             'existing dataset', name)
                raise ValueError(f'External link {name} was not created. A Dataset with this name'
                                 ' already exists and overwrite is set to False! '
                                 'You can pass overwrite=True in order to overwrite the '
                                 'existing dataset')
        else:
            self[name] = h5py.ExternalLink(filename, path)
            return self[name]

    def from_yaml(self, yamlfile: Path):
        """creates groups, datasets and attributes defined in a yaml file.
        Creation is performed relative to the current group level.

        Note the required yaml file structure, e.g.
        datasets:
          grp/supgrp/y:
            data: 2
            overwrite: True
        groups:
          grp/supgrp:
            attrs:
        attrs:
          grp/supgrp:
            comment: This is a group comment
        """
        with open(yamlfile, 'r') as f:
            data = yaml.safe_load(f)

        if 'groups' in data:
            for grp in data['groups']:
                kwargs = data['groups'][grp]
                logger.debug("dumping group defined by yaml file. name: %s, kwargs: %s", grp, kwargs)
                try:
                    self.create_group(grp, **kwargs)
                except Exception as e:
                    logger.critical('Group %s from yaml definition not written due to %s', grp, e)

        if 'datasets' in data:
            for ds in data['datasets']:
                kwargs = data['datasets'][ds]
                logger.debug("dumping dataset defined by yaml file. name: %s, kwargs: %s", ds, kwargs)
                try:
                    self.create_dataset(ds, **kwargs)
                except Exception as e:
                    logger.critical('Dataset %s from yaml definition not written due to %s', ds, e)

        if 'attrs' in data:
            for objname in data['attrs']:
                kwargs = data['attrs'][objname]
                logger.debug(
                    f"dumping attribute data defined by yaml file for {objname}: {kwargs}")
                for ak, av in data['attrs'][objname].items():
                    try:
                        self[objname].attrs[ak] = av
                    except Exception as e:
                        logger.critical('Could not write attribute %s to %s due to %s', ak, objname, e)

    def get_by_attribute(self, attribute_name, attribute_value=None,
                         h5type=None, recursive=True) -> List[Union[h5py.Dataset, h5py.Group]]:
        """Return the object(s) (dataset or group) with a certain attribute name
        and if specified a specific value.
        Via h5type it can be filtered for only datasets or groups

        Parameters
        ----------
        attribute_name: str
            Name of the attribute
        attribute_value: any, default=None
            Value of the attribute. If None, the value is not checked
        h5type: str, default=None
            If specified, looking only for groups or datasets.
            To look only for groups, pass 'group' or 'grp'.
            To look only for datasets, pass 'dataset' or 'ds'.
            Default is None, which looks in both object types.
        recursive: bool, default=True
            If True, scans recursively through all groups below current.

        Returns
        ------
        names: List[h5py.Dataset|h5py.Group]
            List of dataset and/or group objects
        """
        names = []

        def _get_grp(name, node):
            if isinstance(node, h5py.Group):
                if attribute_name in node.attrs:
                    if attribute_value is None:
                        names.append(node)
                    else:
                        if node.attrs[attribute_name] == attribute_value:
                            names.append(node)

        def _get_ds(name, node):
            if isinstance(node, h5py.Dataset):
                if attribute_name in node.attrs:
                    if attribute_value is None:
                        names.append(node)
                    else:
                        if node.attrs[attribute_name] == attribute_value:
                            names.append(node)

        def _get_ds_grp(name, node):
            if attribute_name in node.attrs:
                if attribute_value is None:
                    names.append(node)
                else:
                    if node.attrs[attribute_name] == attribute_value:
                        names.append(node)

        if recursive:
            if h5type is None:
                self.visititems(_get_ds_grp)
            elif h5type.lower() in ('dataset', 'ds'):
                self.visititems(_get_ds)
            elif h5type.lower() in ('group', 'grp', 'gr'):
                self.visititems(_get_grp)
        else:
            if h5type is None:
                for ds in self.values():
                    if attribute_name in ds.attrs:
                        if ds.attrs[attribute_name] == attribute_value:
                            names.append(ds)
            elif h5type.lower() in ('dataset', 'ds'):
                for ds in self.values():
                    if isinstance(ds, h5py.Dataset):
                        if attribute_name in ds.attrs:
                            if ds.attrs[attribute_name] == attribute_value:
                                names.append(ds)
            elif h5type.lower() in ('group', 'grp', 'gr'):
                for ds in self.values():
                    if isinstance(ds, h5py.Group):
                        if attribute_name in ds.attrs:
                            if ds.attrs[attribute_name] == attribute_value:
                                names.append(ds)
        return names

    def get_datasets_by_attribute(self, attribute_name, attribute_value=None,
                                  recursive=True) -> List[h5py.Dataset]:
        """Return datasets that have key-value-attribute pari. Calls `get_by_attribute`"""
        return self.get_by_attribute(attribute_name, attribute_value, 'dataset', recursive)

    def get_groups_by_attribute(self, attribute_name, attribute_value=None,
                                recursive=True) -> List[h5py.Group]:
        """Return groups that have key-value-attribute pari. Calls `get_by_attribute`"""
        return self.get_by_attribute(attribute_name, attribute_value, 'group', recursive)

    def _get_obj_names(self, obj_type, recursive):
        """Return all names of specified object type
        in this group and if recursive==True also
        all below"""
        _names = []

        def _get_obj_name(name, node):
            if isinstance(node, obj_type):
                _names.append(name)

        if recursive:
            self.visititems(_get_obj_name)
            return _names
        return [g for g in self.keys() if isinstance(self[g], obj_type)]

    def get_group_names(self, recursive=True):
        """Return all group names in this group and if recursive==True also
        all below"""
        return self._get_obj_names(h5py.Group, recursive)

    def get_dataset_names(self, recursive=True):
        """Return all dataset names in this group and if recursive==True also
        all below"""
        return self._get_obj_names(h5py.Dataset, recursive)

    def dump(self, collapsed: bool = True, max_attr_length: Union[int, None] = None,
             chunks: bool = False, maxshape: bool = False):
        """Outputs xarray-inspired _html representation of the file content if a
        notebook environment is used

        Parameters
        ----------
        collapsed: bool, optional=True
            Initial tree view is collapsed
        max_attr_length: Union[int, None], optional=None
            Max string length to display.
        chunks: bool, optional=False
            Show chunk
        maxshape: bool, optional=False
            Show maxshape
        """
        if max_attr_length:
            self.hdfrepr.max_attr_length = max_attr_length
        return self.hdfrepr.__html__(self, collapsed=collapsed, chunks=chunks, maxshape=maxshape)

    def _repr_html_(self):
        return self.hdfrepr.__html__(self)

    def sdump(self):
        """string representation of group"""
        return self.hdfrepr.__str__(self)

    def build_xr_dataset(self, *dataset):
        from ..xr.dataset import HDFXrDataset
        return HDFXrDataset(*dataset)


class DatasetValues:
    """helper class to work around xarray"""

    def __init__(self, h5dataset):
        self.h5dataset = h5dataset

    def __getitem__(self, args, new_dtype=None):
        return self.h5dataset.__getitem__(args, new_dtype=new_dtype, nparray=True)

    def __setitem__(self, args, val):
        return self.h5dataset.__setitem__(args, val)


class H5Dataset(h5py.Dataset):
    """Inherited Dataset group of the h5py package"""
    convention = 'default'

    @property
    def attrs(self):
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return WrapperAttributeManager(self)

    @property
    def parent(self) -> "H5Group":
        """Return the parent group of this dataset

        Returns
        -------
        H5Group
            Parent group of this dataset"""

        return self._h5grp(super().parent)

    @property
    def rootparent(self) -> "H5Group":
        """Return the root group of the file.

        Returns
        -------
        H5Group
            Root group object.
        """

        def get_root(p):
            """get the root parent"""
            global found
            found = p.parent

            def search(_parent):
                """recursive search function"""
                global found
                parent = _parent.parent
                if parent.name == '/':
                    found = parent
                else:
                    search(parent)

            search(p)
            return found

        if self.name == '/':
            return self._h5grp(self)
        return self._h5grp(get_root(super().parent))

    @property
    def basename(self) -> str:
        """Basename of the dataset, which is the name without the
        internal file path

        Returns
        -------
        str
            The basename.
        """
        return os.path.basename(self.name)

    @property
    def values(self) -> DatasetValues:
        """Mimic the h5py behaviour and return a numpy array instead
        of a xarray object.

        Returns
        -------
        DatasetValues
            Helper class mimicking the h5py behaviour of returning a numpy array.
        """
        return DatasetValues(self)

    def modify(self, **properties) -> "H5Dataset":
        """modify property of dataset such as `chunks` or `dtpye`. This is
        not possible with the original implementation in `h5py`. Note, that
        this may be a time-consuming task for large datasets! Better to set
        the properties correct already during dataset creation!"""
        return self.parent.modify_dataset_properties(self, **properties)

    def rename(self, new_name):
        """Rename the dataset. This may be time and data intensive as
        a new dataset is created first!"""
        return self.parent.modify_dataset_properties(self, name=new_name)

    def __getattr__(self, item):
        if item not in self.__dict__:
            for d in self.dims:
                if len(d) > 0:
                    for i in range(len(d)):
                        if item == os.path.basename(d[i].name):
                            return d[i]
        return super().__getattribute__(item)

    def __setitem__(self, key, value):
        if isinstance(value, xr.DataArray):
            self.attrs.update(value.attrs)
            super().__setitem__(key, value.data)
        else:
            super().__setitem__(key, value)

    def __getitem__(self, args, new_dtype=None, nparray=False) -> Union[xr.DataArray, np.ndarray]:
        """Return sliced HDF dataset. If global setting `RETURN_XARRAY`
        is set to True, a `xr.DataArray` is returned, otherwise the default
        behaviour of the h5p-package is used and a np.ndarray is returned.
        Note, that even if `RETURN_XARRAY` is True, there is another way to
        receive  numpy array. This is by calling .values[:] on the dataset."""
        args = args if isinstance(args, tuple) else (args,)
        if not CONFIG.RETURN_XARRAY or nparray:
            return super().__getitem__(args, new_dtype=new_dtype)
        if Ellipsis in args:
            warnings.warn(
                'Ellipsis not supported at this stage. returning numpy array')
            return super().__getitem__(args, new_dtype=new_dtype)
        else:
            arr = super().__getitem__(args, new_dtype=new_dtype)
            attrs = pop_hdf_attributes(self.attrs)

            if 'DIMENSION_LIST' in self.attrs:
                # there are coordinates to attach...

                myargs = [slice(None) for _ in range(self.ndim)]
                for ia, a in enumerate(args):
                    myargs[ia] = a

                # remember the first dimension name for all axis:
                dims_names = [Path(d[0].name).stem if len(
                    d) > 0 else f'dim_{ii}' for ii, d in enumerate(self.dims)]

                coords = {}
                used_dims = []
                for dim, dim_name, arg in zip(self.dims, dims_names, myargs):
                    for iax, _ in enumerate(dim):
                        dim_ds = dim[iax]
                        coord_name = Path(dim[iax].name).stem
                        if dim_ds.ndim == 0:
                            if isinstance(arg, int):
                                coords[coord_name] = xr.DataArray(name=coord_name,
                                                                  dims=(
                                                                  ), data=dim_ds[()],
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                            else:
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=coord_name,
                                                                  data=[
                                                                      dim_ds[()], ],
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                        else:
                            used_dims.append(dim_name)
                            _data = dim_ds[arg]
                            if isinstance(_data, np.ndarray):
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=dim_name,
                                                                  data=_data,
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))
                            else:
                                coords[coord_name] = xr.DataArray(name=coord_name, dims=(),
                                                                  data=_data,
                                                                  attrs=pop_hdf_attributes(dim_ds.attrs))

                used_dims = [dim_name for arg, dim_name in zip(
                    myargs, dims_names) if isinstance(arg, slice)]

                COORDINATES = self.attrs.get('COORDINATES')
                if COORDINATES is not None:
                    if isinstance(COORDINATES, str):
                        COORDINATES = [COORDINATES, ]
                    for c in COORDINATES:
                        if c[0] == '/':
                            _data = self.rootparent[c]
                        else:
                            _data = self.parent[c]
                        _name = Path(c).stem
                        coords.update({_name: xr.DataArray(name=_name, dims=(),
                                                           data=_data,
                                                           attrs=pop_hdf_attributes(self.parent[c].attrs))})
                return xr.DataArray(name=Path(self.name).stem, data=arr, dims=used_dims,
                                    coords=coords, attrs=attrs)
            return xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)

    def __repr__(self) -> str:
        r = super().__repr__()
        if not self:
            return r[:-1] + f' (convention "{self.convention}")>'
        else:
            return r[:-1] + f', convention "{self.convention}">'

    def __lt__(self, other):
        """Call __lt__() on group names"""
        return self.name < other.name

    def dump(self) -> None:
        """Call sdump()"""
        self.sdump()

    def sdump(self) -> None:
        """Print the dataset content in a more comprehensive way"""
        out = f'{self.__class__.__name__} "{self.name}"'
        out += f'\n{"-" * len(out)}'
        out += f'\n{"shape:":14} {self.shape}'

        has_dim = False
        dim_str = '\n\nDimensions'
        for _id, d in enumerate(self.dims):
            naxis = len(d)
            if naxis > 0:
                has_dim = True
                for iaxis in range(naxis):
                    if naxis > 1:
                        dim_str += f'\n   [{_id}({iaxis})] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}'
                    else:
                        dim_str += f'\n   [{_id}] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}'
        if has_dim:
            out += dim_str
        print(out)

    def __init__(self, _id):
        if isinstance(_id, h5py.Dataset):
            _id = _id.id
        if isinstance(_id, h5py.h5d.DatasetID):
            super().__init__(_id)
        else:
            ValueError('Could not initialize Dataset. A h5py.h5f.FileID object must be passed')

        super().__init__(_id)

    def to_units(self, new_units: str, inplace: bool = False):
        """Changes the physical unit of the dataset using pint_xarray.
        If `inplace`=True, it loads to full dataset into RAM, which may
        not recommended for very large datasets.
        TODO: think about RAM check or perform it based on chunks"""
        if inplace:
            old_units = self[()].attrs['units']
            self[()] = self[()].pint.quantify().pint.to(new_units).pint.dequantify()
            new_units = self[()].attrs['units']
            logger.debug(f'Changed units of {self.name} from {old_units} to {new_units}.')
        return self[()].pint.quantify().pint.to(new_units).pint.dequantify()

    def rename2(self, newname):
        """renames the dataset. Note this may be a process that kills your RAM"""
        # hard copy:
        if 'CLASS' and 'NAME' in self.attrs:
            raise RuntimeError(
                'Cannot rename {self.name} because it is a dimension scale!')

        self.parent[newname] = self
        del self.parent[self.name]

    def set_primary_scale(self, axis, iscale: int):
        """define the axis for which the first scale should be set. iscale is the index
        of the available scales to be set as primary.
        Make sure you have written intent on file"""
        nscales = len(self.dims[axis])
        if iscale >= nscales:
            raise ValueError(
                f'The target scale index "iscale" is out of range [0, {nscales - 1}]')
        backup_scales = self.dims[axis].items()
        for _, ds in backup_scales:
            self.dims[axis].detach_scale(ds)
        ils = [iscale, *[i for i in range(nscales) if i != iscale]]
        for i in ils:
            self.dims[axis].attach_scale(backup_scales[i][1])
        logger.debug('new primary scale: %s', self.dims[axis][0])


class H5File(h5py.File, H5Group):
    """Main wrapper around h5py.File. It is inherited from h5py.File and h5py.Group.
    It enables additional features and adds new methods streamlining the work with
    HDF5 files and incorporates usage of so-called naming-conventions and layouts.
    All features from h5py packages are preserved."""

    convention = 'default'

    @property
    def attrs(self) -> WrapperAttributeManager:
        """Return an attribute manager that is inherited from h5py's attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    @property
    def version(self) -> str:
        """Return version stored in file"""
        return self.attrs.get('__h5rdmtoolbox_version__')

    @property
    def modification_time(self) -> datetime:
        """Return creation time from file"""
        return datetime.fromtimestamp(self.hdf_filename.stat().st_mtime,
                                      tz=timezone.utc).astimezone()

    @property
    def creation_time(self) -> datetime:
        """Return creation time from file"""
        return datetime.fromtimestamp(self.hdf_filename.stat().st_ctime,
                                      tz=timezone.utc).astimezone()

    @property
    def filesize(self):
        """
        Returns file size in bytes (or other units if asked)

        Returns
        -------
        _bytes
            file size in byte

        """
        _bytes = os.path.getsize(self.filename)
        return _bytes * ureg.byte

    @property
    def layout(self) -> H5Layout:
        """return H5Layout object"""
        return self._layout

    @layout.setter
    def layout(self, layout: Union[Path, str, H5Layout]):
        if isinstance(layout, str):
            self._layout = H5Layout.load_registered(name=layout, h5repr=self.hdfrepr)
        elif isinstance(layout, Path):
            self._layout = H5Layout(layout, self.hdfrepr)
        elif layout is None:
            self._layout = H5Layout.load_registered(name=self.__class__.__name__, h5repr=self.hdfrepr)
        elif isinstance(layout, H5Layout):
            self._layout = layout
        else:
            raise TypeError('Unexpected type for layout. Expect str, pathlib.Path or H5Layout but got '
                            f'{type(layout)}')

    def __init__(self,
                 name: Path = None,
                 mode='r',
                 *,
                 layout: Union[Path, str, H5Layout] = 'H5File',
                 driver=None,
                 libver=None,
                 userblock_size=None,
                 swmr=False,
                 rdcc_nslots=None,
                 rdcc_nbytes=None,
                 rdcc_w0=None,
                 track_order=None,
                 fs_strategy=None,
                 fs_persist=False,
                 fs_threshold=1,
                 **kwds):
        _tmp_init = False
        if name is None:
            _tmp_init = True
            logger.debug("An empty H5File class is initialized")
            name = utils.touch_tmp_hdf5_file()
        elif isinstance(name, ObjectID):
            pass
        elif not isinstance(name, (str, Path)):
            raise ValueError(
                f'It seems that no proper file name is passed: type of {name} is {type(name)}')
        else:
            if mode == 'r+':
                if not Path(name).exists():
                    _tmp_init = True
                    # "touch" the file, so it exists
                    with h5py.File(name, mode='w', driver=driver,
                                   libver=libver, userblock_size=userblock_size, swmr=swmr,
                                   rdcc_nslots=rdcc_nslots, rdcc_nbytes=rdcc_nbytes, rdcc_w0=rdcc_w0,
                                   track_order=track_order, fs_strategy=fs_strategy, fs_persist=fs_persist,
                                   fs_threshold=fs_threshold,
                                   **kwds) as _h5:
                        pass  # just touching the file

        if _tmp_init:
            mode = 'r+'
        if not isinstance(name, ObjectID):
            self.hdf_filename = Path(name)
        super().__init__(name=name,
                         mode=mode,
                         driver=driver,
                         libver=libver,
                         userblock_size=userblock_size,
                         swmr=swmr,
                         rdcc_nslots=rdcc_nslots,
                         rdcc_nbytes=rdcc_nbytes,
                         rdcc_w0=rdcc_w0,
                         track_order=track_order,
                         fs_strategy=fs_strategy,
                         fs_persist=fs_persist,
                         fs_threshold=fs_threshold,
                         **kwds)

        if self.mode != 'r':
            # update file toolbox version, wrapper version
            self.attrs['__h5rdmtoolbox_version__'] = __version__

        self.layout = layout

    def __repr__(self) -> str:
        r = super().__repr__()
        return r.replace('HDF5', f'HDF5 (convention: {self.convention})')

    def __str__(self) -> str:
        return f"<class 'h5rdmtoolbox.H5File' convention: {self.convention}>"

    def check(self, grp: Union[str, h5py.Group] = '/') -> int:
        """Run layout check. This method may be overwritten to add conditional
         checking.

         Parameters
         ----------
         grp: str or h5py.Group, default='/'
            Group from where to start the layout check.
            Per default starts at root level

         Returns
         -------
         int
            Number of detected issues.
         """
        return self.layout.check(self[grp])

    def moveto(self, destination: Path, overwrite: bool = False) -> Path:
        """Move the opened file to a new destination.

        Parameters
        ----------
        destination : Path
            New filename.
        overwrite : bool
            Whether to overwrite an existing file.

        Return
        ------
        new_filepath : Path
            Path to new file locationRaises

        Raises
        ------
        FileExistsError
            If destination file exists and overwrite is False.
        """
        dest_fname = Path(destination)
        if dest_fname.exists() and not overwrite:
            raise FileExistsError(f'The target file "{dest_fname}" already exists and overwriting is set to False.'
                                  ' Not moving the file!')
        logger.debug('Moving file %s to %s', {self.hdf_filename}, dest_fname)

        if not dest_fname.parent.exists():
            Path.mkdir(dest_fname.parent, parents=True)
            logger.debug('Created directory %s', dest_fname.parent)

        mode = self.mode
        self.close()
        shutil.move(self.hdf_filename, dest_fname)
        super().__init__(dest_fname, mode=mode)
        new_filepath = dest_fname.absolute()
        self.hdf_filename = new_filepath
        return new_filepath

    def saveas(self, filename: Path, overwrite: bool = False) -> "H5File":
        """
        Save this file under a new name (effectively a copy). This file is closed and re-opened
        from the new destination using the previous file mode.

        Parameters
        ----------
        filename: Path
            New filename.
        overwrite: bool, default=False
            Whether not to overwrite an existing filename.

        Returns
        -------
        H5File
            Instance of moved H5File

        """
        _filename = Path(filename)
        if _filename.is_file():
            if overwrite:
                os.remove(_filename)
            else:
                raise FileExistsError("Note: File was not moved to new location as a file already exists with this name"
                                      " and overwriting was disabled")

        src = self.filename
        mode = self.mode
        self.close()  # close this instance

        shutil.copy2(src, _filename)
        self.hdf_filename = _filename
        return H5File(_filename, mode=mode)

    def reopen(self, mode: str = 'r+') -> None:
        """Open the closed file"""
        self.__init__(self.hdf_filename, mode=mode)

    @staticmethod
    def open(filename: Union[str, pathlib.Path], mode: str = "r+") -> 'H5File':
        """Open the closed file and use the correct wrapper class

        Parameters
        ----------
        filename: str ot pathlib.Path
            Path to file to be opened
        mode: str
            Mode used to open the file: r, r+, w, w-, x, a

        Returns
        -------
        Subclass of H5File
        """
        return H5File(filename, mode)


H5Dataset._h5grp = H5Group
H5Dataset._h5ds = H5Dataset

H5Group._h5grp = H5Group
H5Group._h5ds = H5Dataset
