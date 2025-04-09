"""Core wrapper module containing basic wrapper implementation of File, Dataset and Group
"""

import json
import logging
import os
import pathlib
import shutil
import warnings
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Union, Tuple, Optional

import h5py
import numpy as np
# noinspection PyUnresolvedReferences
import pint
import rdflib
import xarray as xr
from h5py._hl.base import phil, with_phil
from h5py._objects import ObjectID

# noinspection PyUnresolvedReferences
from . import xr2hdf
from .ds_decoder import dataset_value_decoder
from .h5attr import H5_DIM_ATTRS, pop_hdf_attributes, WrapperAttributeManager
from .h5utils import _is_not_valid_natural_name, get_rootparent
from .. import _repr, get_config, convention, utils, consts, protected_attributes
from .. import get_ureg
from .. import protocols
from .._repr import H5Repr, H5PY_SPECIAL_ATTRIBUTES
from ..convention.consts import DefaultValue
from ..ld import rdf

logger = logging.getLogger('h5rdmtoolbox')

MODIFIABLE_PROPERTIES_OF_A_DATASET = ('name', 'chunks', 'compression', 'compression_opts',
                                      'dtype', 'maxshape')
H5KWARGS = ('driver', 'libver', 'userblock_size', 'swmr',
            'rdcc_nslots', 'rdcc_nbytes', 'rdcc_w0', 'track_order',
            'fs_strategy', 'fs_persist', 'fs_threshold', 'fs_page_size',
            'page_buf_size', 'min_meta_keep', 'min_raw_keep', 'locking',
            'alignment_threshold', 'alignment_interval', 'meta_block_size')


def assert_filename_existence(filename: pathlib.Path) -> pathlib.Path:
    """Raises an error if the filename does not exist. Otherwise, the filename is returned.

    Parameters
    ----------
    filename : pathlib.Path
        Filename to check.

    Returns
    -------
    pathlib.Path
        The filename if it exists.

    Raises
    ------
    FileNotFoundError
        If the filename does not exist.
    """
    if not filename.exists():
        raise FileNotFoundError('Filename does not exist. It might be moved or deleted!')
    return filename


def convert_strings_to_datetimes(array, time_format='%Y-%m-%dT%H:%M:%S.%f'):
    assert np.issubdtype(array.dtype, np.str_), 'Unexpected array type'
    return np.array([datetime.strptime(date_str, time_format) for date_str in array.flat]).reshape(array.shape)
    # else:
    #     return np.array([convert_strings_to_datetimes(subarray) for subarray in array])


def _pop_standard_attributes(kwargs, cache_entry) -> Tuple[Dict, Dict]:
    """Pop all standard attributes from kwargs and return them in a dict."""
    std_attrs = {}
    for k in cache_entry.keys():
        if k in kwargs:
            std_attrs[k] = kwargs.pop(k)
    return kwargs, std_attrs


class Lower(str):
    """Lower"""

    def __new__(cls, string):
        instance = super().__new__(cls, string.lower())
        return instance


def lower(string: str) -> str:
    """return object Lower(string). Used when a dataset
    is called, but the upper/lower case should be irrelevant."""
    return Lower(string)


def process_attributes(cls,
                       meth_name: str,
                       attrs: Dict,
                       kwargs: Dict,
                       name: str,
                       existing_attrs: Optional[Tuple] = None) -> Tuple[Dict, Dict, Dict]:
    """Process attributes and kwargs for methods "create_dataset", "create_group" and "File.__init__" method.

    Parameters
    ----------
    cls : type
        Class of the method.
    meth_name : str
        Name of the method.
    attrs : Dict
        Attributes of the method.
    kwargs : Dict
        Keyword arguments of the method.
    name : str
        Name of the dataset or group to be created.
    existing_attrs: Optional[Tuple]
        Tuple of existing attributes. If an attribute is in this tuple, it is not considered as a standard attribute.
    """
    if existing_attrs is None:
        existing_attrs = list()

    curr_cv = convention.get_current_convention()

    # go through list of registered standard attributes, and check whether they are in kwargs:
    if meth_name not in curr_cv.methods[cls]:
        return attrs, {}, kwargs

    # transfer all standard attributes from kwargs to skwargs:
    kwargs, skwargs = _pop_standard_attributes(
        kwargs, cache_entry=curr_cv.methods[cls][meth_name]
    )

    # pop standard attributes if the file already have such a attribute. Note, that no validation is performed then!
    for n in existing_attrs:
        skwargs.pop(n, None)

    # attrs overwrite skwargs because kwargs could have the default value
    for ak in skwargs.keys():
        v = attrs.pop(ak, None)
        if v is not None:
            if ak in skwargs:
                # potential conflict
                # if the skwargs is not set and not required, pass attrs to skwargs
                # same accounts if the current value in skwargs is the default (to be identified by instance check)
                if skwargs[ak] == DefaultValue.NONE or skwargs[ak] == DefaultValue.EMPTY or isinstance(skwargs[ak],
                                                                                                       DefaultValue) \
                        or skwargs[ak] is None:
                    skwargs[ak] = v
                # else raise error
                else:
                    raise convention.standard_attributes.errors.StandardAttributeError(
                        f'You passed the standard attribute "{ak}" as a standard argument and it is '
                        f'also in the "attrs" argument. This is not allowed!')

    _pop = []
    # only consider non-None standard attributes
    for k, v in skwargs.items():
        if isinstance(v, (str, DefaultValue)):
            if v == DefaultValue.NONE:
                _pop.append(k)  # dont consider values with DefaultValue.NONE
            elif v == DefaultValue.EMPTY:
                # None may be only a placeholder, but a real value is expected
                # this is the case if the registered default value is DefaultValue.EMPTY:
                alt_attr_name = curr_cv.methods[cls][meth_name][k].alternative_standard_attribute
                if alt_attr_name in skwargs:
                    logger.debug(
                        f'Standard attribute {k} is empty and alternative standard attribute given by the user')
                    if skwargs[alt_attr_name] == DefaultValue.EMPTY:
                        raise convention.standard_attributes.errors.StandardAttributeError(
                            f'Error creating {cls.__name__} "{name}": The standard attribute "{k}" '
                            f'is required but not provided. The alternative '
                            f'{alt_attr_name} '
                            f'is also not provided.')
                    else:
                        logger.debug(f'Remove standard attribute {k} from the parameters and use alternative: '
                                     f'{alt_attr_name}')
                        _pop.append(k)
                else:
                    logger.debug(f'Standard attribute {k} is empty but no alternative attribute given by the user.')
                    if not get_config('ignore_set_std_attr_err'):
                        raise convention.standard_attributes.errors.StandardAttributeError(
                            f'The standard attribute "{k}" is required but not provided.')

    _ = [skwargs.pop(p) for p in _pop]

    # # standard attributes may be passed as arguments or in attrs. But if they are passed in both an error is raised!
    # for skey, vas in skwargs.items():
    #     if skey in attrs:
    #         if vas is None:
    #             # pass over the attribute value to the skwargs dict:
    #             skwargs[skey] = attrs[skey]
    #         else:
    #             raise convention.standard_attributes.errors.StandardAttributeError(
    #                 f'You passed the standard attribute "{skey}" as a standard argument and it is '
    #                 f'also in the "attrs" argument. This is not allowed!')

    attrs.update(skwargs)
    return attrs, skwargs, kwargs


def _delattr(obj: protocols.H5TbxHLObject, item: str):
    if obj.standard_attributes.get(item, None):
        if get_config('allow_deleting_standard_attributes'):
            del obj.attrs[item]
            return
        raise ValueError('Deleting standard attributes is not allowed based on the current configuration! '
                         'You may change this by calling '
                         '"h5tbx.set_config(allow_deleting_standard_attributes=True)".')
    if item in obj and get_config('natural_naming'):
        del obj[item]
        return
    del obj[item]
    # super().__delattr__(item)


class Group(h5py.Group):
    """Inherited Group of the package h5py. Adds some useful methods on top
    of the underlying *h5py* package.


    .. note:: All features from h5py packages are preserved.


    Notes
    -----
    The following methods are added:
    * get_datasets() - returns a list of datasets in the group
    * get_groups() - returns a list of groups in the group
    * get_tree_structure() - returns a tree structure of the group
    * create_string_dataset() - creates a dataset with string datatype
    * create_time_dataset() - creates a dataset with time datatype

    The following properties are added (or overwritten):
    * attrs - returns the *h5tbx* attribute manager, which is a subclass of the *h5py* attribute manager
    * rdf - returns the RDF Manager
    * rootparent - returns the root group instance
    * basename - returns the basename of the group
    """
    hdfrepr = H5Repr()

    @property
    def hdf_filename(self) -> pathlib.Path:
        """The filename of the file, even if the HDF5 file is closed."""
        return assert_filename_existence(self._hdf_filename)

    @property
    def attrs(self):
        """Calls the wrapper attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    @property
    def rootparent(self):
        """Return the root group instance."""
        if self.name == '/':
            return File(self._id)
        return File(get_rootparent(self.parent)._id)

    rootgroup = rootparent  # alias

    @property
    def basename(self) -> str:
        """Basename of dataset (path without leading forward slash)"""
        return os.path.basename(self.name)

    def get_datasets(self, pattern: str = '.*', recursive: bool = False) -> List[h5py.Dataset]:
        """Return list of datasets in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the datasets."""
        if pattern == '.*' and not recursive:
            return [v for v in self.values() if isinstance(v, h5py.Dataset)]
        return [self.rootparent[ds.name] for ds in
                self.find({'$name': {'$regex': pattern}}, '$Dataset', recursive=recursive)]

    def get_groups(self,
                   pattern: str = '.*',
                   recursive: bool = False) -> List[h5py.Group]:
        """Return list of groups in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the groups."""
        if pattern == '.*' and not recursive:
            return [v for v in self.values() if isinstance(v, h5py.Group)]
        # if return_lazy:
        #     return self.find({'$name': {'$regex': pattern}}, '$Group', recursive=recursive)
        return [self.rootparent[g.name] for g in
                self.find({'$name': {'$regex': pattern}}, '$Group', recursive=recursive)]

    def __init__(self, _id):
        if isinstance(_id, h5py.Group):
            _id = _id.id
        if isinstance(_id, h5py.h5g.GroupID):
            super().__init__(_id)
        else:
            raise ValueError('Could not initialize Group. A h5py.h5f.FileID object must be passed')
        self._hdf_filename = Path(self.file.filename)

    def __setitem__(self,
                    name: str,
                    obj: Union[xr.DataArray, List, Tuple, Dict, h5py.ExternalLink]) -> protocols.H5TbxDataset:
        """
        Lazy creating datasets. More difficult than using h5py as mandatory
        parameters must be provided.

        Parameters
        ----------
        name: str
            Name of dataset
        obj: xr.DataArray or Dict or List/Tuple of data and metadata.
                    If obj is not a xr.DataArray, data must be provided using a list or tuple.
                    See examples for possible ways to pass data.

        Returns
        -------
        None
        """
        if isinstance(obj, xr.DataArray):
            return Dataset(obj.hdf.to_group(Group(self), name).id)
        if isinstance(obj, (list, tuple)):
            if not isinstance(obj[1], dict):
                raise TypeError(f'Second item must be type dict but is {type(obj[1])}')
            kwargs = obj[1]
            return self.create_dataset(name, data=obj[0], **kwargs)
        if isinstance(obj, dict):
            return self.create_dataset(name=name, **obj)
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
        if isinstance(ret, h5py.Group):
            return self._h5grp(ret.id)

    def __getattr__(self, item: str):
        standard_attributes: Dict = self.standard_attributes
        if standard_attributes:  # are there standard attributes registered?
            standard_attribute: Optional[protocols.StandardAttribute] = standard_attributes.get(item, None)
            if standard_attribute:  # is there an attribute requested with name=item available?
                return standard_attribute.get(self)

        try:
            return super().__getattribute__(item)
        except (RuntimeError, AttributeError) as e:
            if not get_config('natural_naming'):
                # raise an error if natural naming is NOT enabled
                raise AttributeError(e)

        # if item in self.__dict__:
        #     return super().__getattribute__(item)
        try:
            _item = item.replace('_', ' ')
            # item is a Group name?
            if item in [k for k, v in self.items() if isinstance(v, h5py.Group)]:
                return self._h5grp(self[item].id)
            # item is a Dataset name?
            elif item in [k for k, v in self.items() if isinstance(v, h5py.Dataset)]:
                return self._h5ds(self[item].id)
            raise AttributeError(item)
            # return super().__getattribute__(item)
        except AttributeError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        if self.__class__ in convention.get_current_convention().properties:
            if key in convention.get_current_convention().properties[self.__class__]:
                return convention.get_current_convention().properties[self.__class__][key](self).set(value)
        super().__setattr__(key, value)

    def __str__(self) -> str:
        return f'<HDF5 wrapper group "{self.name}" (members: {len(self)}, convention: "{convention.get_current_convention().name}")>'

    def __repr__(self) -> str:
        return self.__str__()

    def __lt__(self, other):
        return self.name < other.name

    def __delattr__(self, item):
        _delattr(self, item)

    @property
    def convention(self):
        """Return the convention currently enabled."""
        return convention.get_current_convention()

    @property
    def standard_attributes(self) -> Dict:
        """Return the standard attributes of the class."""
        return self.convention.properties.get(self.__class__, {})

    @property
    def rdf(self):
        """Return RDF Manager"""
        return rdf.RDFManager(self.attrs)

    @property
    def frdf(self):
        """Via the File RDF Manager, semantic properties can be associated with the file rather than the
        root group. If you want to describe a root attribute semantically, use `.rdf` instead.

        .. versionadded:: 1.6.0
           Explanation of the new feature, or additional notes if necessary.
        """
        if self.name == "/":
            return rdf.FileRDFManager(self.attrs)
        return rdf.FileRDFManager(self.rootparent.attrs)

    @property
    def iri(self):
        """Deprecated. Use rdf instead."""
        warnings.warn('Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning)
        return rdf.RDFManager(self.attrs)

    # @property
    # def attrsdef(self) -> definition.DefinitionManager:
    #     """Return DefinitionManager"""
    #     return definition.DefinitionManager(self.attrs)

    def get_tree_structure(self, recursive=True, ignore_attrs: List[str] = None):
        """Return the tree (attributes, names, shapes) of the group and subgroups"""
        if ignore_attrs is None:
            ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        tree = dict(self.attrs.items())
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
                     rdf_type: Optional[Union[str, rdflib.URIRef]] = None,
                     rdf_subject: Optional[Union[str, rdflib.URIRef]] = None,
                     update_attrs: Optional[bool] = False,
                     track_order=None,
                     **kwargs) -> "Group":
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
            ... overwrite is None, then h5py behaviour is enabled meaning that if a group exists h5py will raise
            ... overwrite is True, then group is deleted and rewritten according to method parameters
            ... overwrite is False, then group creation has no effect. Existing group is returned.
        attrs : dict, optional
            Attributes of the group, default is None which is an empty dict
        update_attrs: bool, optional
            If overwrite is False, whether to update the attributes or not. Default is False.
        track_order : bool or None
            Track creation order under this group. Default is None.
        """
        if attrs is None:
            attrs = {}

        attrs, skwargs, kwargs = process_attributes(Group, 'create_group', attrs, kwargs, name)
        if name in self:
            if not isinstance(self[name], h5py.Group):
                raise ValueError('The name you passed is already used for a dataset!')

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

        if _is_not_valid_natural_name(self, name, get_config('natural_naming')):
            raise ValueError(f'The group name "{name}" is not valid. It is an '
                             f'attribute of the class and cannot be used '
                             f'while natural naming is enabled')

        subgrp = super().create_group(name, track_order=track_order)

        # new_subgroup = h5py.Group.create_group(self, name, track_order=track_order)
        logger.debug(f'Created group "{name}" at "{self.name}"-level.')

        h5tbxgrp = self._h5grp(subgrp)
        if attrs:
            for k, v in attrs.items():
                try:
                    h5tbxgrp.attrs[k] = v
                except convention.standard_attributes.errors.StandardAttributeError as e:
                    del self[name]  # undo group creation
                    raise e
        if rdf_type is not None:
            h5tbxgrp.rdf.type = rdf_type
        if rdf_subject:
            h5tbxgrp.rdf.subject = rdf_subject
        return h5tbxgrp

    def create_time_dataset(self,
                            name: str,
                            data: Union[datetime, List],
                            time_format: str,
                            assign_rdf: bool = True,
                            overwrite: bool = False,
                            attrs: Dict = None,
                            **kwargs):
        """Special creation function to create a time vector. Data is stored as a string dataset
        where each datetime is converted to a string using the provided time_format

        Parameter
        ---------
        name : str
            Name of the dataset
        data : Union[datetime, List]
            Data to be stored. If a list is provided, each element must be a datetime object
        time_format : str
            Format of the time string. E.g. '%Y-%m-%dT%H:%M:%S.%f' or 'iso'. If 'iso' is provided
            the format is set to '%Y-%m-%dT%H:%M:%S.%f'
        assign_rdf : bool, default=True
            Automatically assign RDF to dataset. This includes type='https://schema.org/DateTime' and
            predicate for time_format='https://matthiasprobst.github.io/pivmeta#timeFormat'
            This is True by default
        overwrite : bool, default=False
            If the dataset already exists, it is overwritten if True. If False, the dataset is not created
        attrs : Dict, default=None
            Attributes of the dataset
        **kwargs : dict
            Additional keyword arguments passed to the h5py create_dataset method
        """
        if attrs is None:
            attrs = {}
        if time_format.lower() == 'iso':
            time_format = '%Y-%m-%dT%H:%M:%S.%f'

        attrs.update({'time_format': time_format})

        if isinstance(data, np.ndarray):
            ds = self.create_string_dataset(name,
                                            data=[t.astype(datetime).strftime(time_format) for t in data],
                                            overwrite=overwrite,
                                            attrs=attrs,
                                            **kwargs)
        else:
            _data = np.asarray(data)
            _orig_shape = _data.shape
            _flat_data = _data.flatten()
            _flat_data = np.asarray([t.strftime(time_format) for t in _flat_data])
            _reshaped_data = _flat_data.reshape(_orig_shape)
            ds = self.create_string_dataset(name, data=_reshaped_data.tolist(),
                                            overwrite=overwrite, attrs=attrs, **kwargs)
        if assign_rdf:
            ds.rdf.type = 'https://schema.org/DateTime'
            ds.rdf['time_format'].predicate = 'https://matthiasprobst.github.io/pivmeta#timeFormat'
        return ds

    def create_string_dataset(self,
                              name: str,
                              data: Union[str, List[str]],
                              overwrite=False,
                              attrs=None,
                              rdf_type: Optional[Union[str, rdflib.URIRef]] = None,
                              **kwargs):
        """Create a string dataset. In this version only one string is allowed.
        In future version a list of strings may be allowed, too.
        No long or standard name needed"""

        if attrs is None:
            attrs = {}

        attrs, skwargs, kwargs = process_attributes(Group, 'create_string_dataset', attrs, kwargs, name)

        if isinstance(data, str):
            n_letter = len(data)
        elif isinstance(data, (tuple, list)):
            n_letter = max([len(d) for d in np.asarray(data).flatten()])
        else:
            raise TypeError(f'Unexpected type for parameter "data": {type(data)}. Expected str or List/Tuple of str')
        dtype = f'S{max(1, n_letter)}'
        if name in self:
            if overwrite is True:
                del self[name]  # delete existing dataset
            # else let h5py return the error

        if isinstance(data, str):
            compression = None
            compression_opts = None
        else:
            compression = kwargs.pop('compression', get_config('hdf_compression'))
            compression_opts = kwargs.pop('compression_opts', get_config('hdf_compression_opts'))

        make_scale = kwargs.pop('make_scale', False)
        ds = super().create_dataset(name, dtype=dtype, data=data, **kwargs,
                                    compression=compression, compression_opts=compression_opts)
        if make_scale:
            if isinstance(data, str):
                ds.make_scale(make_scale)
            else:
                ds.make_scale()

        for ak, av in attrs.items():
            ds.attrs[ak] = av
        if rdf_type is not None:
            ds.rdf.type = rdf_type
        return self._h5ds(ds.id)

    def create_dataset(self,
                       name,
                       shape=None,
                       dtype=None,
                       data=None,
                       overwrite=None,
                       chunks=None,
                       make_scale=False,
                       attach_data_scale=None,
                       attach_data_offset=None,
                       attach_scales=None,
                       ancillary_datasets=None,
                       rdf_type: Optional[Union[str, rdflib.URIRef]] = None,
                       attrs=None,
                       **kwargs  # standard attributes and other keyword arguments
                       ) -> protocols.H5TbxDataset:
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
            - ... overwrite is None, then h5py behaviour is enabled meaning that if a dataset exists h5py will raise an error
            - ... overwrite is True, then dataset is deleted and rewritten according to method parameters
            - ... overwrite is False, then dataset creation has no effect. Existing dataset is returned.
        chunks : bool or according to h5py.File.create_dataset documentation
            Needs to be True if later resizing is planned
        make_scale: bool, default=False
            Makes this dataset scale. The parameter attach_scale must be uses, thus be None.
        attach_data_scale: Union[None, h5py.Dataset], default=None
            If not None, attach this dataset as scale to the dataset.
        attach_data_offset: Union[None, h5py.Dataset], default=None
            If not None, attach this dataset as offset to the dataset.
        attach_scales : tuple, optional
            Tuple defining the datasets to attach scales to. Content of tuples are
            internal hdf paths. If an axis should not be attached to any axis leave it
            empty (''). Default is ('',) which attaches no scales
            Note: internal hdf5 path is relative w.r.t. this dataset, so be careful
            where to create the dataset and to which to attach the scales!
            Also note, that if data is a xr.DataArray and attach_scales is not None,
            coordinates of xr.DataArray are ignored and only attach_scales is
            considered.
        ancillary_datasets: Union[None, Dict[h5py.Dataset]], optional=None
            If not None, attach flags to dataset. If str, it is interpreted as
            internal hdf path. If h5py.Dataset, it is interpreted as dataset to attach
            flags to. Default is None, which means no flags are attached. If a flag
            dataset is attached the return object is a xr.Dataset object, which additionally
            includes the flag data array.
        attrs : dict, optional
            Allows to set attributes directly after dataset creation. Default is
            None, which is an empty dict
        **kwargs : dict, optional
            Dictionary of standard arguments and other keyword arguments that are passed
            to the parent function.
            For **kwargs, see h5py.File.create_dataset.

            Standard arguments are defined by a convention and hence expected keywords
            depend on the registered standard attributes.

        Returns
        -------
        ds : h5py.Dataset
            created dataset
        """

        if isinstance(data, str):
            if attach_data_scale is not None or attach_data_offset is not None:
                raise ValueError('Cannot set data_scale or data_offset for string datasets.')
            return self.create_string_dataset(name=name,
                                              data=data,
                                              overwrite=overwrite,
                                              attrs=attrs,
                                              rdf_type=rdf_type,
                                              **kwargs)
        if attrs is None:
            attrs = {}

        if ancillary_datasets is None:
            ancillary_datasets = {}

        if isinstance(data, xr.DataArray):
            if dtype:
                data = data.astype(dtype)
            attrs.update(data.attrs)
            data.name = name

        if attach_scales is None:
            # maybe there's a typo:
            attach_scales = kwargs.pop('attach_scale', None)

        if attach_scales is not None:
            if not isinstance(attach_scales, (list, tuple)):
                attach_scales = (attach_scales,)
            if any([True for a in attach_scales if a]) and make_scale:
                raise ValueError(
                    'Cannot make scale and attach scale at the same time!')

        attrs, skwargs, kwargs = process_attributes(Group, 'create_dataset', attrs, kwargs, name=name)

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
        compression = kwargs.pop('compression', get_config('hdf_compression'))
        compression_opts = kwargs.pop('compression_opts', get_config('hdf_compression_opts'))

        if shape is not None:
            if len(shape) == 0:
                compression, compression_opts, chunks = None, None, None

        if name:
            if _is_not_valid_natural_name(self, name, get_config('natural_naming')):
                raise ValueError(f'The dataset name "{name}" is not a valid. It is an '
                                 f'attribute of the class and cannot be used '
                                 f'while natural naming is enabled')

        if isinstance(data, xr.DataArray):
            if attach_scales:
                for dim, scale in zip(data.dims, attach_scales):
                    if isinstance(scale, str):
                        scale_name = scale
                        scale_data = self[scale].values[()]
                    elif isinstance(scale, h5py.Dataset):
                        scale_name = scale.name
                        scale_data = scale[()]
                    else:
                        raise TypeError(f'Expecting type string or a h5py.Dataset for scale, not {type(scale)}')
                    data = data.rename({dim: scale_name}).assign_coords({scale_name: scale_data})
            attrs.update(data.attrs)
            xrds = data.hdf.to_group(self._h5grp(self), name=name,
                                     overwrite=overwrite,
                                     compression=compression,
                                     compression_opts=compression_opts,
                                     attrs=attrs)
            return Dataset(xrds.id)

        if not isinstance(make_scale, (bool, str)):
            raise TypeError(f'Make scale must be a boolean or a string not {type(make_scale)}')

        if isinstance(shape, np.ndarray):  # needed if no keyword is used
            data = shape
            shape = None

        if data is not None:
            _data = np.asarray(data)
        else:
            _data = data

        if ancillary_datasets:
            for anc_name, anc_ds in ancillary_datasets.items():
                if not isinstance(anc_ds, h5py.Dataset):
                    raise TypeError(f'Expected ancillary dataset to be of type h5py.Dataset, '
                                    f'but got {type(anc_ds)}')
                if anc_ds.shape != _data.shape:
                    raise ValueError(f'Associated dataset {anc_name} has shape {anc_ds.shape} '
                                     f'which does not match dataset shape {_data.shape}')
            attrs[consts.ANCILLARY_DATASET] = json.dumps({k: v.name for k, v in ancillary_datasets.items()})

        _maxshape = kwargs.get('maxshape', shape)

        logger.debug(f'Creating dataset "{name}" in "{self.name}" with maxshape "{_maxshape}" '
                     f'and using compression "{compression}" with opt "{compression_opts}"')

        # if possible, create dataset with shape first:
        if _data is not None:
            if _data.ndim == 0:
                # create 0D dataset
                _ds = super().create_dataset(name,
                                             shape=shape,
                                             dtype=dtype,
                                             data=_data,
                                             **kwargs)
            else:
                # create ND dataset with shape, data is assigned later
                _ds = super().create_dataset(name,
                                             shape=shape,
                                             dtype=dtype,
                                             data=_data,
                                             chunks=chunks,
                                             compression=compression,
                                             compression_opts=compression_opts,
                                             **kwargs)
        else:
            # no data given, initialize with shape only
            _ds = super().create_dataset(name, shape=shape, dtype=dtype, data=_data,
                                         compression=compression,
                                         compression_opts=compression_opts,
                                         chunks=chunks,
                                         **kwargs)

        ds = Dataset(_ds.id)

        if rdf_type is not None:
            ds.rdf.type = rdf_type

        if attach_data_scale is not None or attach_data_offset is not None:
            units = attrs.get('units', None)
            if units:
                ds.attrs['units'] = units
            ds.attach_data_scale_and_offset(attach_data_scale, attach_data_offset)

        # assign attributes, which may raise errors if attributes are standardized and not fulfill requirements:
        if attrs:
            for k, v in attrs.items():
                try:
                    # call __setitem__ because then we can pass attrs which is needed by the potential validators of
                    # standard attributes
                    if isinstance(v, h5py.Dataset):
                        ds.attrs.__setitem__(k, v.name, attrs)
                    else:
                        ds.attrs.__setitem__(k, v, attrs)
                except convention.standard_attributes.errors.StandardAttributeError as e:
                    logger.debug(f'Could not set attribute "{k}" with value "{v}" to dataset "{name}" for convention '
                                 f'{self.convention.name}. Orig err: "{e}"')
                    del self[name]
                    raise e

        # what is this for? uncommented it in version v1.0.1
        # if isinstance(data, np.ndarray):
        #     if data is not None and data.ndim > 0:
        #         ds[()] = data

        # make scale
        if make_scale:
            if isinstance(make_scale, bool):
                ds.make_scale('')
            elif isinstance(make_scale, str):
                ds.make_scale(make_scale)

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
                            ds_to_attach = ss
                        else:
                            ds_to_attach = self[ss]

                        shape_of_axis_i = ds.shape[i]
                        if ds_to_attach.ndim != 1:
                            raise ValueError(f'Cannot only attach 1D datasets, but got '
                                             f'{ds_to_attach.ndim}D dataset {ds_to_attach.name}')
                        if not shape_of_axis_i == ds_to_attach.shape[0]:
                            del self[ds.name]
                            raise ValueError(f'Cannot assign {ds_to_attach.name} to {name} because it has '
                                             f'different shape {ds_to_attach.shape[0]} than {shape_of_axis_i}')
                        ds.dims[i].attach_scale(ds_to_attach)
        return ds

    def find_one(self,
                 flt: Union[Dict, str],
                 objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
                 recursive: bool = True,
                 ignore_attribute_error: bool = False) -> protocols.LazyObject:
        """See ObjDB.find_one()"""
        from h5rdmtoolbox.database import ObjDB
        return ObjDB(self).find_one(flt, objfilter, recursive, ignore_attribute_error)

    def find(self,
             flt: Union[Dict, str, List[str]],
             objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
             recursive: bool = True,
             ignore_attribute_error: bool = False) -> List[protocols.LazyObject]:
        """
        Examples for filter parameters:
        filter = {'long_name': 'any objects long name'} --> searches in attributes only
        filter = {'$name': '/name'}  --> searches in groups and datasets for the (path)name
        filter = {'$basename': 'name'}  --> searches in groups and datasets for the basename (without path)

        Parameters
        ----------
        flt: Dict
            Filter request
        objfilter: str | h5py.Dataset | h5py.Group | None
            Filter. Default is None. Otherwise, only dataset or group types are returned.
        recursive: bool, optional
            Recursive search. Default is True
        ignore_attribute_error: bool, optional=False
            If True, the KeyError normally raised when accessing hdf5 object attributes is ignored.
            Otherwise, the KeyError is raised.

        Returns
        -------
        h5obj: List[LazyObject]
        """
        from h5rdmtoolbox.database import ObjDB
        return ObjDB(self).find(flt,
                                objfilter,
                                recursive=recursive,
                                ignore_attribute_error=ignore_attribute_error)

    def create_dataset_from_csv(self, csv_filename: Union[str, pathlib.Path], *args, **kwargs):
        """Create datasets from a single csv file. Docstring: See File.create_datasets_from_csv()"""
        return self.create_datasets_from_csv(csv_filenames=[csv_filename, ], *args, **kwargs)

    def create_datasets_from_csv(self,
                                 csv_filenames: Union[str, pathlib.Path, List[Union[str, pathlib.Path]]],
                                 dimension: Union[int, str] = 0,
                                 shape=None,
                                 overwrite=False,
                                 combine_opt='stack',
                                 axis=0,
                                 chunks=None,
                                 attrs: Dict = None,
                                 **pandas_kwargs):
        """
        Reads data from a csv and adds a dataset according to column names.
        Pandas.read_csv() is used. So all arguments for this function may be passed.

        Parameters
        ----------
        csv_filenames : Path or list of Path
            CSV filename or list of filenames.
            If list is passed, structure must be the same for all
        dimension : Union[int, str], optional=0
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
        try:
            import pandas as pd
        except ImportError:
            raise ImportError('pandas is required for this function')

        if combine_opt not in ['concatenate', 'stack']:
            raise ValueError(f'Invalid input for combine_opt: {combine_opt}')

        if attrs is None:
            attrs = {}
        if 'names' in pandas_kwargs.keys():
            if 'header' not in pandas_kwargs.keys():
                raise RuntimeError('Missing "header" argument for pandas.read_csv')

        if isinstance(csv_filenames, (list, tuple)):
            n_files = len(csv_filenames)
            dfs = [pd.read_csv(csv_fname, **pandas_kwargs) for csv_fname in csv_filenames]
        elif isinstance(csv_filenames, (str, Path)):
            n_files = 1
            dfs = [pd.read_csv(csv_filenames, **pandas_kwargs), ]
        else:
            raise ValueError(
                f'Wrong input for "csv_filenames: {type(csv_filenames)}')

        compression, compression_opts = get_config('hdf_compression'), get_config('hdf_compression_opts')

        if n_files > 1 and combine_opt == 'concatenate':
            dfs = [pd.concat(dfs, axis=axis), ]
            n_files = 1

        if n_files == 1:
            datasets = []

            column_names = dfs[0].columns
            dataset_names = [utils.remove_special_chars(str(variable_name)) for variable_name in column_names]

            if dimension is None:
                dimension = ''
            else:
                if shape:
                    raise ValueError('shape must be None if dimension is not None')
                if not isinstance(dimension, (int, str)):
                    raise TypeError(f'Invalid input for dimension: {type(dimension)}. Expected int or str')
                if isinstance(dimension, int):
                    dimension = column_names[dimension]

            for ds_name, variable_name in zip(dataset_names, column_names):
                ds_name = utils.remove_special_chars(str(variable_name))
                if shape is not None:
                    data = dfs[0][str(variable_name)].values.reshape(shape)
                else:
                    data = dfs[0][str(variable_name)].values
                try:
                    datasets.append(self.create_dataset(name=ds_name,
                                                        data=data,
                                                        attrs=attrs.get(ds_name, None),
                                                        overwrite=overwrite, compression=compression,
                                                        compression_opts=compression_opts,
                                                        make_scale=variable_name == dimension,
                                                        chunks=chunks))
                except RuntimeError as e:
                    logger.error(
                        f'Could not read {variable_name} from csv file due to: {e}')

            # attach scale if dimension is set
            if dimension:
                for ds, variable_name in zip(datasets, column_names):
                    if variable_name != dimension:
                        ds.dims[0].attach_scale(self[dimension])
            for ds in datasets:
                ds.attrs['source_filename'] = csv_filenames
                if isinstance(csv_filenames, (list, tuple)):
                    ds.attrs['source_filename_hash_md5'] = [utils.get_checksum(f) for f in csv_filenames]
                else:
                    ds.attrs['source_filename_hash_md5'] = utils.get_checksum(csv_filenames)
            return datasets

        data = {}
        for name, value in dfs[0].items():
            if shape is None:
                data[name] = [value.values, ]
            else:
                data[name] = [value.values.reshape(shape), ]
        for df in dfs[1:]:
            for name, value in df.items():
                if shape is None:
                    data[name].append(value.values)
                else:
                    data[name].append(value.values.reshape(shape))

        for name, value in data.items():
            ds = self.create_dataset(name=str(name),
                                     data=np.stack(value, axis=axis),
                                     attrs=attrs.get(name, None),
                                     overwrite=overwrite,
                                     compression=compression,
                                     compression_opts=compression_opts,
                                     chunks=chunks)

            ds.attrs['source_filename'] = csv_filenames
            ds.attrs['source_filename_has_md5'] = [utils.get_checksum(f) for f in csv_filenames]

    def create_dataset_from_image(self,
                                  img_data: Union[Iterable, np.ndarray, List[np.ndarray]],
                                  name,
                                  chunks=None,
                                  dtype=None,
                                  axis=0,
                                  **kwargs):
        """
        Creates a dataset for a single or multiple files. If a list of filenames is passed
        All images are stacked (thus shape of all images must be equal!)

        Parameters
        ----------
        img_data : np.ndarray or list of np.ndarray
            Image filename or list of image file names. See also axis in case of multiple files
        name : str
            Name of create dataset
        chunks : Tuple or None
            Data chunking
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
        _compression, _compression_opts = get_config('hdf_compression'), get_config('hdf_compression_opts')
        compression = kwargs.pop('compression', _compression)
        compression_opts = kwargs.pop('compression_opts', _compression_opts)
        first_image = None
        n = None

        if axis not in (0, -1):
            raise ValueError(f'Parameter for parameter axis can only be 0 or 1 but not {axis}')

        iterable: bool = isinstance(img_data, Iterable)
        if iterable:
            # check if img_data has method __len__():
            if not hasattr(img_data, '__len__'):
                raise ValueError('img_data must have method __len__()')
            n = len(img_data)

            img_data = iter(img_data)

            # get first element of img_data:
            first_image = next(img_data)
            single_img_shape = first_image.shape
            if axis == 0:
                shape = (n, *single_img_shape)
                chunks = (1, *single_img_shape)
            else:
                shape = (*single_img_shape, n)
                chunks = (*single_img_shape, 1)
        else:
            if isinstance(img_data, np.ndarray):
                shape = img_data.shape
            else:
                shape = None

        ds = self.create_dataset(name=name,
                                 shape=shape,
                                 compression=compression,
                                 compression_opts=compression_opts,
                                 chunks=chunks,
                                 dtype=dtype,
                                 **kwargs)
        if isinstance(img_data, np.ndarray):
            ds[()] = img_data
            return ds

        assert first_image is not None, 'First image is None. This should not happen!'
        if axis == 0:
            ds[0, ...] = first_image
        else:
            ds[..., 0] = first_image

        for i in range(1, n):
            if axis == 0:
                ds[i, ...] = next(img_data)
            else:
                ds[..., i] = next(img_data)
        return ds

    def create_dataset_from_xarray_dataset(self, dataset: xr.Dataset) -> None:
        """creates the xr.DataArrays of the passed xr.Dataset, writes all attributes
        and handles the dimension scales."""
        ds_coords = {}
        for coord in dataset.coords.keys():
            ds = self.create_dataset(str(coord),
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
            logger.debug('External link %s was not created. A Dataset with this name'
                         ' already exists and overwrite is set to False! '
                         'You can pass overwrite=True in order to overwrite the '
                         'existing dataset', name)
            raise ValueError(f'External link {name} was not created. A Dataset with this name'
                             ' already exists and overwrite is set to False! '
                             'You can pass overwrite=True in order to overwrite the '
                             'existing dataset')
        self[name] = h5py.ExternalLink(filename, path)
        return self[name]

    def create_from_yaml(self, yaml_filename: Path, num_dtype: Optional[str] = None):
        """creates groups, datasets and attributes defined in a yaml file.
        Creation is performed relative to the current group level.

        If a num_dtype is provided, all numerical datasets are created with this dtype.

        An example YAML file content could look like this:

        >>> title: 'Title of the file'
        >>> contact: '0000-1234-1234-1234'
        >>> grp:
        >>>   attrs:
        >>>     comment: test
        >>> grp/subgrp/y:
        >>>   data: 2
        >>>   overwrite: True
        >>>   attrs:
        >>>     units: 'm/s'
        >>> grp/subgrp:
        >>>   attrs:
        >>>     comment: This is a group comment
        >>>   velocity:
        >>>     data: [3.4, 1.1]
        >>>     overwrite: True
        >>>     attrs:
        >>>       units: 'm/s'

        Examples
        --------
        >>> with h5tbx.File('test.h5', 'w') as h5:
        >>>     h5.create_from_yaml('test.yaml')
        """
        from . import h5yaml
        h5yaml.H5Yaml(yaml_filename).write(self, num_dtype=num_dtype)

    def create_from_dict(self, dictionary: Dict):
        """Create groups and datasets based on a dictionary"""
        from . import h5yaml
        h5yaml.H5Dict(dictionary).write(self)

    def create_from_jsonld(self, data: str, context: Optional[Dict] = None):
        """Create groups/datasets from a jsonld string."""
        from . import jsonld
        jsonld.to_hdf(self, data=json.loads(data), context=context)

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

    def dump(self,
             collapsed: bool = True,
             max_attr_length: Union[int, None] = None,
             chunks: bool = False,
             maxshape: bool = False) -> None:
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

    def sdump(self, hide_uri: bool = False):
        """string representation of group"""
        return self.hdfrepr.str_repr(self, hide_uri=hide_uri)

    dumps = sdump


class DatasetValues:
    """helper class to work around xarray"""

    def __init__(self, h5dataset):
        self.h5dataset = h5dataset

    def __getitem__(self, args, new_dtype=None):
        return self.h5dataset.__getitem__(args, new_dtype=new_dtype, nparray=True)

    def __setitem__(self, args, val):
        return self.h5dataset.__setitem__(args, val)


def only_0d_and_1d(obj):
    """Decorator to check if the dataset is 1D"""

    def wrapper(*args):
        if args[0].ndim > 1:
            raise ValueError('Only applicable to 0D and 1D datasets!')

    return obj


class Dataset(h5py.Dataset):
    """Wrapper around the h5py.Dataset. Some useful methods are added on top of
    the underlying *h5py* package.


    .. note:: All features from h5py packages are preserved.


    Notes
    -----
    The following methods are added to the *h5py.Dataset* object:

    * attach_ancillary_dataset(): Associate a dataset to the current dataset.
    * attach_data_scale_and_offset(): Attach data scale and offset to the current dataset.
    * detach_data_offset(): Detach data offset from the current dataset.
    * detach_data_scale(): Detach data scale from the current dataset.
    * coords(): Return the coordinates of the current dataset similar to xarray.
    * dump(): Outputs xarray-inspired _html representation of the file content if a notebook environment is used.
    * dumps(): string representation of group
    * isel(): Select data by named dimension and index, mimics xarray.isel.
    * sel(): Select data by named dimension and values, mimics xarray.sel.

    The following properties are added to the h5py.Dataset object:

    * rootparent: The root group of the file.
    * basename: The basename of the dataset.
    * values: Accessor to return numpy array of the dataset.
    """

    @only_0d_and_1d
    def __lt__(self, other: Union[int, float, protocols.H5TbxDataset]):
        if isinstance(other, (int, float)):
            data = self.values[()]
            if data.ndim == 1:
                return np.where(data < other)[0]
            return data < other
        # to sort lists of datasets:
        return self.name < other.name

    @only_0d_and_1d
    def __le__(self, other: Union[int, float]):
        if not isinstance(other, (int, float)):
            raise ValueError('Can only compare to floats and integers!')
        data = self.values[()]
        if data.ndim == 1:
            return np.where(data <= other)[0]
        return data <= other

    @only_0d_and_1d
    def __gt__(self, other: Union[int, float]):
        if not isinstance(other, (int, float)):
            raise ValueError('Can only compare to floats and integers!')
        data = self.values[()]
        if data.ndim == 1:
            return np.where(data > other)[0]
        return data > other

    @only_0d_and_1d
    def __ge__(self, other: Union[int, float]):
        if not isinstance(other, (int, float)):
            raise ValueError('Can only compare to floats and integers!')
        data = self.values[()]
        if data.ndim == 1:
            return np.where(data >= other)[0]
        return data >= other

    @only_0d_and_1d
    def __eq__(self, other: Union[int, float, str, h5py.Dataset]):
        if isinstance(other, h5py.Dataset):
            return self.id == other.id
        if isinstance(other, str):
            return self.name == other

        if isinstance(other, (int, float)):
            data = self.values[()]
            if data.ndim == 1:
                return np.where(data == other)[0]
            return data == other

        raise ValueError(f'Unexpected type to compare to: "{type(other)}"')

    @with_phil
    def __hash__(self):
        return hash(self.id)

    def __delattr__(self, item):
        _delattr(self, item)

    @property
    def convention(self):
        """Return the convention currently enabled."""
        return convention.get_current_convention()

    @property
    def standard_attributes(self) -> Dict:
        """Return the standard attributes of the class."""
        return self.convention.properties.get(self.__class__, {})

    @property
    def rdf(self):
        """Return RDF Manager"""
        return rdf.RDFManager(self.attrs)

    @property
    def iri(self):
        """Deprecated. Use rdf instead."""
        warnings.warn('Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning)
        return rdf.RDFManager(self.attrs)

    @property
    def hdf_filename(self) -> pathlib.Path:
        """The filename of the file, even if the HDF5 file is closed."""
        return assert_filename_existence(self._hdf_filename)

    @property
    def attrs(self) -> protocols.H5TbxAttributeManager:
        """Exact copy of parent class:
        Attributes attached to this object """
        with phil:
            return WrapperAttributeManager(self)

    @property
    def parent(self) -> protocols.H5TbxGroup:
        """Return the parent group of this dataset

        Returns
        -------
        Group
            Parent group of this dataset"""

        return self._h5grp(super().parent)

    @property
    def rootparent(self) -> "Group":
        """Return the root group of the file.

        Returns
        -------
        Group
            Root group object.
        """
        return self.parent.rootparent

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

    @property
    def ancillary_datasets(self) -> Dict:
        """Return a dictionary of ancillary datasets attached to this dataset. The dictionary
        contains the name(s) (hdf internal path) and the dataset object(s)."""

        def _to_ds(parent, source):
            if isinstance(source, str):
                return parent[source]
            if isinstance(source, Dataset):
                return source
            return Dataset(source)

        anc_ds = self.attrs.get(consts.ANCILLARY_DATASET, {})
        if anc_ds:
            return {name: _to_ds(self.parent, path) for name, path in anc_ds.items()}
        return {}

    def attach_ancillary_dataset(self, ancillary_dataset: Union[str, h5py.Dataset]):
        """Attach a flag dataset to the current dataset. The flag dataset
        must have the same shape as the current dataset.

        Parameters
        ----------
        ancillary_dataset : Union[str, h5py.Dataset]
            The ancillary dataset to be attached to this dataset. Can be a string (internal hdf name)
            or a h5py.Dataset object.

        Returns
        -------
        Dataset
            The current dataset object.
        """
        if isinstance(ancillary_dataset, str):
            ancillary_dataset = self.parent[ancillary_dataset]
        if ancillary_dataset.shape != self.shape:
            raise ValueError('Shape of flag dataset does not match the shape of the current dataset!')
        ancillary_datasets = self.ancillary_datasets
        ancillary_datasets[ancillary_dataset.basename] = ancillary_dataset.name
        self.attrs[consts.ANCILLARY_DATASET] = ancillary_datasets
        return self

    def detach_data_scale(self):
        """Remove the attached data scale dataset from this dataset."""
        warnings.warn('Note, that detaching data scale may influence the correctness and traceability of your data',
                      UserWarning)
        self.attrs.pop('DATA_SCALE', None)

    def detach_data_offset(self):
        """Remove the attached data offset dataset from this dataset."""
        warnings.warn('Note, that detaching data offset may influence the correctness and traceability of your data',
                      UserWarning)
        self.attrs.pop('DATA_OFFSET', None)

    def attach_data_scale_and_offset(self, scale: Union[None, h5py.Dataset], offset: Union[None, h5py.Dataset]):
        """Attach a data scale and offset to this dataset. The scale and offset must have the same"""
        if self.attrs.get('IS_DATA_SCALE', False):
            raise ValueError('Cannot attach data scale to a dataset, which is already a data scale!')
        if self.attrs.get('IS_DATA_OFFSET', False):
            raise ValueError('Cannot attach data offset to a dataset, which is already a data offset!')
        if 'units' not in self.attrs:
            raise ValueError('Cannot attach data scale if no attribute "units" is not set!')

        this_units = get_ureg().Unit(self.attrs.get('units', ''))

        # try:
        if scale is not None:
            scaled_units = this_units * get_ureg().Unit(scale.attrs.get('units', ''))
        else:
            scaled_units = this_units

        if offset is not None:
            if scaled_units.dimensionality == get_ureg().Unit(offset.attrs.get('units', '')).dimensionality:
                pass
            else:
                raise ValueError('Units of scale and offset must be compatible!')

        if scale is not None:
            self.attrs['DATA_SCALE'] = scale.name
        if offset is not None:
            self.attrs['DATA_OFFSET'] = offset.name

    def get_data_scale(self):
        """Return the data scale dataset if attached to this dataset."""
        if 'DATA_SCALE' in self.attrs:
            _src = self.attrs['DATA_SCALE']
            if isinstance(_src, str):
                return self.rootparent[_src]
            return self.rootparent[self.attrs['DATA_SCALE'].name]
        return None

    def get_data_offset(self):
        """Return the data offset dataset if attached to this dataset."""
        if 'DATA_OFFSET' in self.attrs:
            _src = self.attrs['DATA_OFFSET']
            if isinstance(_src, str):
                return self.rootparent[_src]
            return self.rootparent[self.attrs['DATA_OFFSET'].name]
        return None

    @property
    def coords(self) -> Dict:
        """Return a dictionary of the dimension scales of the dataset.
        Corresponds to the xarray coordinates."""
        coords = {}
        for dim in self.dims:
            if len(dim) > 0:
                for i, d in enumerate(dim):
                    coords[dim[i].name.rsplit('/')[-1]] = dim[i]
        return coords
        # return {d[0].name.rsplit('/')[-1]: d[0] for d in self.dims if len(d) > 0}

    def assign_coord(self, coord):
        if isinstance(coord, str):
            if coord not in self.rootparent:
                raise ValueError(f'Coordinate {coord} not found in the file!')
            coord = self.rootparent[coord]
        curr_coords = self.attrs.get(protected_attributes.COORDINATES, [])
        curr_coords.append(coord.name)
        self.attrs[protected_attributes.COORDINATES] = curr_coords

        # if coords is not None:
        #     if not isinstance(coords, list):
        #         coords = [coords]
        #     for c in coords:
        #         if not isinstance(c, h5py.Dataset):
        #             raise ValueError('Only h5py.Dataset objects can be assigned as coordinates!')
        #         coords_kwargs.update({c.name: c})
        #
        # for k, v in coords_kwargs.items():
        #
        #     if not isinstance(v, h5py.Dataset):
        #         if not isinstance(v, xr.DataArray):
        #             raise TypeError(f'Only h5py.Dataset or xarray.DataArray objects can be assigned as coordinates, '
        #                             f'but got {type(v)}')
        #         raise TypeError('Only h5py.Dataset objects can be assigned as coordinates!')
        #
        #     if v.ndim not in (0, self.ndim):
        #         raise ValueError(f'Coordinate {k} must have the same dimension as the dataset or be a scalar!')
        #     elif isinstance(v, xr.DataArray):
        #         self.parent.create_dataset_from_xarray_dataset(v)
        #
        # curr_coords = self.attrs.get(protected_attributes.COORDINATES, {})
        # curr_coords.update(coords_kwargs)
        # self.attrs[protected_attributes.COORDINATES] = curr_coords

    def isel(self, **indexers) -> xr.DataArray:
        """Index selection by providing the coordinate name.

        Parameters
        ----------
        indexers: Dict
            Dictionary with coordinate name as key and slice or index as value

        Returns
        -------
        xr.DataArray
            The sliced HDF5 dataset.

        Exampels
        --------
        >>> with h5tbx.File(filename) as h5:
        >>>     h5.vel.isel(time=0, z=3)
        """
        if len(indexers) == 0:
            return self[()]
        ds_coords = self.coords
        if ds_coords:
            for cname in indexers.keys():
                if cname not in ds_coords:
                    raise KeyError(f'Coordinate {cname} not in {list(ds_coords.keys())}')

            sl = {cname: slice(None) for cname, _ in zip(ds_coords.keys(), range(self.ndim))}
            sl_key_list = list(sl.keys())
            for (cname, item), _ in zip(indexers.items(), range(self.ndim)):
                # if the indexer name is in the same dimension as one of the already registered
                # coordinates in "sl", then replace
                _replaced = False
                for idim, d in enumerate(self.dims):
                    for i in range(len(d)):
                        if d[i].name.rsplit('/')[-1] == cname:
                            sl[sl_key_list[idim]] = item
                            _replaced = True
                            break
                if not _replaced:
                    sl[cname] = item
            # for k in sl.copy().keys():
            #     if k not in indexers:
            #         sl.pop(k)
        else:
            # no indexers available. User must provide dim_<i> then!
            if not all([cname.startswith('dim_') for cname in indexers.keys()]):
                raise KeyError(f'No coordinates available. Provide dim_<i> as key!')
            dim_dict = {f'dim_{i}': slice(None) for i in range(len(self.shape))}
            # indices = [int(cname.split('_')[1]) for cname in indexers.keys()]
            sl = {cname: slice(None) for cname, _ in zip(dim_dict.keys(), range(self.ndim))}
            for (cname, item), _ in zip(indexers.items(), range(self.ndim)):
                sl[cname] = item

        def _make_ascending(_data):
            if isinstance(_data, (np.ndarray, list)):
                # warnings.warn(
                #     'Only ascending order is supported for np.ndarray and list. Reducing the data to unique values'
                # )
                unique_data = np.unique(_data)
                _diff = np.diff(unique_data)
                if np.all(_diff == 1):
                    # more efficient to use slice
                    return slice(unique_data[0], unique_data[-1] + 1, 1)
                if np.all(_diff == 2):
                    # more efficient to use slice
                    return slice(unique_data[0], unique_data[-1] + 1, 2)
                return unique_data
            return _data

        return self[tuple([_make_ascending(v) for v in sl.values()])]

    def sel(self, method=None, **coords):
        """Select data based on coordinates and specific value(s). This is useful if the index
        is not known. Only works for a single dimension and for method 'exact'."""
        av_coord_datasets = self.coords
        isel = {}
        for coord_name, coord_values in coords.items():
            if coord_name not in av_coord_datasets:
                raise KeyError(f'Coordinate {coord_name} not in {list(av_coord_datasets.keys())}')
            sel_coord_data = av_coord_datasets[coord_name][()]
            if method is None or method == 'exact':
                idx = np.where(sel_coord_data == coord_values)[0]

                if idx.size == 0:
                    raise ValueError(
                        f'No matching coordinate found for coordinate {coord_name} and value {coord_values}. '
                        f'Consider using method "nearest".')
                if len(idx) == 1:
                    idx = int(idx[0])

            elif method == 'nearest':
                # idx = (sel_coord_data - coord_values).argmin()[()]
                # print(idx)
                if not isinstance(coord_values, (int, float)):
                    _coord_values = np.array(coord_values)
                    if _coord_values.ndim != 1:
                        raise NotImplementedError('Cuurently .sel() only allows 0D or 1D data for coord_values')
                    _absmins = [np.abs(sel_coord_data - cv) for cv in coord_values]
                    idx = [int(np.argmin(_absmin)) for _absmin in _absmins]
                else:
                    _absmin = np.abs(sel_coord_data - coord_values)
                    idx = int(np.argmin(_absmin))
            else:
                raise NotImplementedError('Only exact and nearest match method implemented')
            isel[coord_name] = idx
        return self.isel(**isel)

    def __getattr__(self, item):
        standard_attributes = self.standard_attributes
        if standard_attributes:
            standard_attribute = standard_attributes.get(item, None)
            if standard_attribute:
                return standard_attribute.get(self)

        if item not in self.__dict__:
            for d in self.dims:
                if len(d) > 0:
                    for i in range(len(d)):
                        if item == os.path.basename(d[i].name):
                            return self.__class__(d[i])
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        if self.__class__ in convention.get_current_convention().properties:
            if key in convention.get_current_convention().properties[self.__class__]:
                return convention.get_current_convention().properties[self.__class__][key].set(self, value)
        return super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if isinstance(value, xr.DataArray):
            self.attrs.update(value.attrs)
            super().__setitem__(key, value.data)
        else:
            super().__setitem__(key, value)

    @dataset_value_decoder
    def __getitem__(self,
                    args,
                    new_dtype=None,
                    nparray=False,
                    links_as_strings: bool = False) -> Union[xr.DataArray, np.ndarray]:
        """Return sliced HDF dataset. If global setting `return_xarray`
        is set to True, a `xr.DataArray` is returned, otherwise the default
        behaviour of the h5p-package is used and a np.ndarray is returned.
        Note, that even if `return_xarray` is True, there is another way to
        receive  numpy array. This is by calling .values[:] on the dataset.

        Parameters
        ----------
        links_as_strings: bool
            Attributes, that are links to other datasets or groups are returned as strings.
        """

        args = args if isinstance(args, tuple) else (args,)

        if not get_config('return_xarray') or nparray:
            return super().__getitem__(args, new_dtype=new_dtype)

        # check if any entry in args is of type Ellipsis:
        if any(arg is Ellipsis for arg in args):
            # substitute Ellipsis with as many slices as needed:
            args = list(args)
            ellipsis_index = args.index(Ellipsis)
            args.pop(ellipsis_index)
            args[ellipsis_index:ellipsis_index] = [slice(None)
                                                   for _ in range(self.ndim - len(args))]
            args = tuple(args)

        arr = super().__getitem__(args, new_dtype=new_dtype)

        if links_as_strings:
            attrs = dict(self.attrs)
            for k, v in attrs.copy().items():
                if isinstance(v, (h5py.Group, h5py.Dataset)):
                    attrs[k] = v.name
            ds_attrs = attrs
        else:
            ds_attrs = self.attrs

        attrs = pop_hdf_attributes(ds_attrs)

        if 'DIMENSION_LIST' in ds_attrs:
            # there are coordinates to attach...

            myargs = [slice(None) for _ in range(self.ndim)]
            for ia, a in enumerate(args):
                myargs[ia] = a

            # remember the first dimension name for all axis:
            dims_names = [d[0].name.rsplit('/')[-1] if len(
                d) > 0 else f'dim_{ii}' for ii, d in enumerate(self.dims)]

            coords = {}

            for dim, dim_name, arg in zip(self.dims, dims_names, myargs):
                for iax, _ in enumerate(dim):
                    dim_ds = dim[iax]
                    coord_name = dim[iax].name.rsplit('/')[-1]
                    if dim_ds.ndim == 0:
                        dim_ds_data = dim_ds[()]
                    else:
                        dim_ds_data = dim_ds[arg]
                    dim_ds_attrs = pop_hdf_attributes(dim_ds.attrs)
                    if dim_ds_data.dtype.kind == 'S':
                        # decode string array
                        if dim_ds_attrs.get('time_format', False):
                            if dim_ds_data.ndim == 0:
                                dim_ds_data = np.array(
                                    datetime.strptime(dim_ds_data.astype(str), dim_ds_attrs['time_format'])).astype(
                                    datetime)
                            else:
                                dim_ds_data = convert_strings_to_datetimes(dim_ds_data.astype(str))
                                # dim_ds_data = np.array(
                                #     [datetime.fromisoformat(t) for t in dim_ds_data.astype(str)]).astype(
                                #     datetime)
                    if dim_ds_data.ndim == 0:
                        if isinstance(arg, int):
                            coords[coord_name] = xr.DataArray(name=coord_name,
                                                              dims=(
                                                              ),
                                                              data=dim_ds_data,
                                                              attrs=dim_ds_attrs)
                        else:
                            coords[coord_name] = xr.DataArray(name=coord_name, dims=coord_name,
                                                              data=[dim_ds[()], ],
                                                              attrs=dim_ds_attrs)
                    else:
                        if isinstance(dim_ds_data, np.ndarray):
                            coords[coord_name] = xr.DataArray(name=coord_name, dims=dim_name,
                                                              data=dim_ds_data,
                                                              attrs=dim_ds_attrs)
                        else:
                            coords[coord_name] = xr.DataArray(name=coord_name, dims=(),
                                                              data=dim_ds_data,
                                                              attrs=dim_ds_attrs)

            used_dims = [dim_name for arg, dim_name in zip(
                myargs, dims_names) if isinstance(arg, (slice, np.ndarray, list))]

            coordinates: Optional[Union[str, List[str]]] = ds_attrs.get(protected_attributes.COORDINATES)
            if coordinates is not None:
                if isinstance(coordinates, str):
                    coordinates = [coordinates, ]
                else:
                    coordinates = list(coordinates)

                for c in coordinates:
                    if c[0] == '/':
                        _data = self.rootparent[c]
                    else:
                        _data = self.parent[c]
                    _name = Path(c).stem
                    coords.update({_name: xr.DataArray(name=_name, dims=(),
                                                       data=_data,
                                                       attrs=pop_hdf_attributes(self.parent[c].attrs))})
            return xr.DataArray(name=Path(self.name).stem,
                                data=arr,
                                dims=used_dims,
                                coords=coords,
                                attrs=attrs)
        # check if arr is string
        if self.dtype == 'object':
            pass
        elif arr.dtype.kind == 'S':
            # decode string array
            try:
                _arr = arr.astype(str)
            except UnicodeDecodeError:
                return xr.DataArray(arr, attrs=attrs)

            time_format = self.attrs.get('time_format', None)
            if time_format is not None:
                if time_format.lower() == 'iso':
                    time_format = '%Y-%m-%dT%H:%M:%S.%f'
                if _arr.ndim == 0:
                    _arr = np.asarray(datetime.strptime(_arr, time_format))
                elif _arr.ndim == 1:
                    _arr = [datetime.strptime(str(t), time_format) for t in _arr]
                else:  # _arr.ndim > 1:
                    orig_shape = _arr.shape
                    _flat_arr = np.asarray([datetime.strptime(t, time_format) for t in _arr.flatten()])
                    _arr = _flat_arr.reshape(orig_shape)
                return xr.DataArray(_arr, attrs=attrs)

            if isinstance(_arr, np.ndarray):
                return xr.DataArray(_arr, attrs=attrs)
            return _arr

        coords = {}
        coordinates: Optional[Union[str, List[str]]] = ds_attrs.get(protected_attributes.COORDINATES, None)
        if coordinates is not None:
            if isinstance(coordinates, str):
                coordinates = [coordinates, ]
            else:
                coordinates = list(coordinates)

            for c in coordinates:
                if c[0] == '/':
                    _data = self.rootparent[c]
                else:
                    _data = self.parent[c]
                _name = Path(c).stem
                coords.update({_name: xr.DataArray(name=_name, dims=(),
                                                   data=_data,
                                                   attrs=pop_hdf_attributes(self.parent[c].attrs))})
            da = xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)
            for k, v in coords.items():
                da = da.assign_coords({k: v})
            return da
        return xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)

    def __repr__(self) -> str:
        r = super().__repr__()
        if not self:
            return r[:-1] + f' (convention "{convention.get_current_convention().name}")>'
        else:
            return r[:-1] + f', convention "{convention.get_current_convention().name}">'

    def dump(self) -> None:
        """Call sdump()"""
        self.sdump()

    def sdump(self) -> None:
        """Print the dataset content in a more comprehensive way"""
        out = f'{self.__class__.__name__} "{self.name}"'
        out += f'\n{"-" * len(out)}'
        out += f'\n{"*shape:":14} {self.shape}'
        out += f'\n{"*dtype:":14} {self.dtype}'
        out += f'\n{"*compression:":14} {self.compression} ({self.compression_opts})'

        for k, v in self.attrs.items():
            out += f'\n{k + ":":14} {v}'

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

    dumps = sdump

    def __init__(self, _id):
        if isinstance(_id, h5py.Dataset):
            _id = _id.id
        if isinstance(_id, h5py.h5d.DatasetID):
            super().__init__(_id)
        else:
            raise ValueError(f'Could not initialize Dataset with type(_id)={type(_id)}. '
                             'A h5py.h5f.FileID object must be passed')

        super().__init__(_id)
        self._hdf_filename = Path(self.file.filename)

    def set_primary_scale(self, axis, iscale: int):
        """Set the primary scale for a specific axis.

        Parameters
        ----------
        axis : int
            The axis index
        iscale : int
            The index of the scale to be set as primary

        Notes
        -----
        Ensure that you have opened the file in read/write mode.
        """
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


class File(h5py.File, Group):
    """Main wrapper around h5py.File.

    Adds additional features and methods to h5py.File in order to streamline the work with
    HDF5 files and to incorporate usage of metadata (attribute naming) convention.
    An additional argument is added to the h5py.


    .. note:: All features from h5py packages are preserved.


    Parameters
    ----------
    filename : str
        The name of the file to open. If the file mode is 'w' or 'r+' and the file does not exist,
        a temporary file is created in the user's temporary directory.
    mode : {'r', 'r+', 'w', 'w-', 'x', 'a'}, optional
        The mode in which to open the file. The default is 'r'.
    **kwargs : Dict
        Additional keyword arguments are passed to h5py.File.


    Notes
    -----
    The following methods are added to the h5py.File object:

    * moveto(): Move the file to a new location.
    * saveas(): Save the file to a new location.
    * reopen(): Reopen the closed file.

    The following attributes are added to the h5py.File object:

    * rdf: RDF Manager
    * hdf_filename: (pathlib.Path) The name of the file, accessible even if the file is closed.
    * version: (str) The version of the package used to create the file.
    * modification_time: (datetime) The modification time of the file.
    * creation_time: (datetime) The creation time of the file.
    * filesize: (int) The size of the file in bytes.

    .. seealso:: :class:`h5rdmtoolbox.core.Group`
    """

    @property
    def attrs(self) -> WrapperAttributeManager:
        """Return an attribute manager that is inherited from h5py's attribute manager"""
        with phil:
            return WrapperAttributeManager(self)

    @property
    def version(self) -> str:
        """Return version stored in file, which is the package version used at the time of creation.
        Not necessarily the current version of the package."""
        return self.get('h5rdmtoolbox', {}).attrs.get('__h5rdmtoolbox_version__')

    @property
    def modification_time(self) -> datetime:
        """Return the modification from the file. Not stored as an attribute!"""
        return datetime.fromtimestamp(self._hdf_filename.stat().st_mtime,
                                      tz=timezone.utc).astimezone()

    @property
    def creation_time(self) -> datetime:
        """Return the creation time from the file. Not stored as an attribute!"""
        return datetime.fromtimestamp(self._hdf_filename.stat().st_ctime,
                                      tz=timezone.utc).astimezone()

    @property
    def filesize(self):
        """
        Returns file size in units of bytes.

        Returns
        -------
        pint.Quantity
            The file size in units of bytes.

        """
        return utils.get_filesize(self.filename)

    def __init__(self,
                 name: Union[str, Path] = None,
                 mode: str = None,
                 attrs: Dict = None,
                 **kwargs):
        is_fileobj_init = False
        # path is file object:
        if isinstance(name, ObjectID):
            # filter out standard attributes from kwargs:
            if "__init__" in convention.get_current_convention().methods[self.__class__]:
                kwargs, _ = _pop_standard_attributes(
                    kwargs, cache_entry=convention.get_current_convention().methods[self.__class__]["__init__"]
                )
            super(File, self).__init__(name, mode, **kwargs)
            self._hdf_filename = Path(self.filename)
            return
        elif hasattr(name, 'read') and hasattr(name, 'seek'):
            super(File, self).__init__(name, mode, **kwargs)
            self._hdf_filename = Path(self.filename)
            is_fileobj_init = True
            super(File, self).__init__(name, mode, **kwargs)

        if not is_fileobj_init:
            # name is path or None:
            if name is None:
                _tmp_init = True
                logger.debug("An empty File class is initialized")
                name = utils.touch_tmp_hdf5_file()
                if mode is None:
                    mode = 'r+'
                else:
                    mode = mode
            elif isinstance(name, (str, pathlib.Path)):
                logger.debug('A filename is given to initialize the File class')
                fname = pathlib.Path(name)
                # a filename is given.

                if mode is None:  # mode not given:
                    # file does exist and mode not given --> read only!
                    if fname.exists():
                        mode = 'r'
                        logger.debug('Mode is set to "r" because file exists and mode was not given.')

                    # file does not exist and mode is not given--> write!
                    elif not fname.exists():
                        raise FileNotFoundError(f'File "{fname}" does not exist and mode is not given.')

                elif mode == 'w' and fname.exists():
                    fname.unlink()
                    logger.debug('File exists and mode is set to "w". Deleting file first.')
                # else mode is given, so just continue... may be correct, may be not... let h5py find out

            if mode is None:
                logger.debug('Mode not set. Set it to "r" by default')
                mode = 'r'
            elif not isinstance(name, (str, Path)):
                raise ValueError(
                    f'It seems that no proper file name is passed: type of "{name}" is {type(name)}'
                )
            else:
                if mode == 'r+':
                    if not Path(name).exists():
                        _tmp_init = True
                        # mode = 'r+'
                        # "touch" the file, so it exists
                        _h5pykwargs = kwargs.copy()
                        for k in list(kwargs.keys()):
                            if k not in H5KWARGS:
                                _h5pykwargs.pop(k, None)
                        with h5py.File(name, mode='w', **_h5pykwargs) as _h5:
                            pass  # just touching the file
                        logger.debug(f'An empty File class is initialized for "{name}".Mode is set to "r+"')

            if attrs is None:
                attrs = {}

            if mode == 'r':
                # check for required standard attributes
                if "__init__" in convention.get_current_convention().methods[self.__class__]:
                    kwargs, skwargs = _pop_standard_attributes(
                        kwargs, cache_entry=convention.get_current_convention().methods[self.__class__]["__init__"]
                    )
                    logger.debug('The file mode is read only ("r"). Provided standard attributes are ignored: '
                                 f'{skwargs.keys()}')
                # ignore standard attributes during read-only
                skwargs = {}
            else:
                # note, that in r+ mode, some attributes may already exist which are mandatory!
                # get existing first:
                if pathlib.Path(name).exists():
                    with h5py.File(pathlib.Path(name), mode='r') as _h5:
                        existing_attrs = tuple(_h5.attrs.keys())
                else:
                    existing_attrs = None
                attrs, skwargs, kwargs = process_attributes(self.__class__, '__init__', attrs, kwargs, name,
                                                            existing_attrs=existing_attrs)

            if mode == 'r' and len(skwargs) > 0:
                for k, v in skwargs.items():
                    if v is not None:
                        raise ValueError(f'Cannot set attribute {k} in read mode')

            # if not isinstance(name, ObjectID):
            #     self._hdf_filename = Path(name)
            logger.debug(f'Initializing h5py.File with name={name}, mode={mode} and kwargs={kwargs}')
            try:
                super().__init__(name=name,
                                 mode=mode,
                                 **kwargs)
            except OSError as e:
                logger.error(f"Unable to open file {name}. Error message: {e}")
                from ..utils import DownloadFileManager
                DownloadFileManager().remove_corrupted_file(name)

                raise e
            self._hdf_filename = Path(self.filename)

            if self.mode != 'r':
                # update file toolbox version, wrapper version
                if get_config('auto_create_h5tbx_version'):
                    if 'h5rdmtoolbox' not in self and get_config('auto_create_h5tbx_version'):
                        utils.create_h5tbx_version_grp(self)
                        # logger.debug('Creating group "h5rdmtoolbox" with attribute "__h5rdmtoolbox_version__" in file')
                        # _tbx_grp = self.create_group('h5rdmtoolbox')
                        # _tbx_grp.rdf.subject = 'https://schema.org/SoftwareSourceCode'
                        # _tbx_grp.attrs['__h5rdmtoolbox_version__', 'https://schema.org/softwareVersion'] = __version__
                for k, v in attrs.items():
                    self.attrs[k] = v

    def __setattr__(self, key, value):
        props = self.convention.properties.get(self.__class__, None)
        if props:
            prop = props.get(key, None)
            if prop:  # does the object have a standard attribute with name stored in key?
                return prop.set(self, value)
        if key.startswith('_'):
            return super().__setattr__(key, value)
        raise AttributeError(f'Cannot set attribute {key} in {self.__class__}. Only standard attributes are allowed '
                             f'to be set in this way. "{key}" seems not be standardized in the current convention. ')

    def __repr__(self) -> str:
        r = super().__repr__()
        return r.replace('HDF5', f'HDF5 (convention: "{convention.get_current_convention().name}")')

    def __str__(self) -> str:
        return f'<class "{self.__class__.__name__}" convention: "{convention.get_current_convention().name}">'

    def __delattr__(self, item):
        _delattr(self, item)

    @property
    def convention(self):
        """Return the convention currently enabled."""
        return convention.get_current_convention()

    @property
    def standard_attributes(self) -> Dict:
        """Return the standard attributes of the class."""
        return self.convention.properties.get(self.__class__, {})

    @property
    def rdf(self):
        """Return RDF Manager"""
        return rdf.RDFManager(self.attrs)

    @property
    def iri(self):
        """Deprecated. Use rdf instead."""
        warnings.warn('Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning)
        return rdf.RDFManager(self.attrs)

    # @property
    # def attrsdef(self) -> definition.DefinitionManager:
    #     """Return DefinitionManager"""
    #     return definition.DefinitionManager(self.attrs)

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
        logger.debug('Moving file %s to %s', {self._hdf_filename}, dest_fname)

        if not dest_fname.parent.exists():
            Path.mkdir(dest_fname.parent, parents=True)
            logger.debug('Created directory %s', dest_fname.parent)

        mode = self.mode
        self.close()
        shutil.move(self._hdf_filename, dest_fname)
        super().__init__(dest_fname, mode=mode)
        new_filepath = dest_fname.absolute()
        self._hdf_filename = new_filepath
        return new_filepath

    def saveas(self, filename: Path, overwrite: bool = False) -> "File":
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
        File
            Instance of moved File

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
        self._hdf_filename = _filename
        return File(_filename, mode=mode)

    def reopen(self, mode: str = 'r+') -> None:
        """Open the closed file"""
        self.__init__(self._hdf_filename, mode=mode)

    @staticmethod
    def open(filename: Union[str, pathlib.Path], mode: str = "r+") -> 'File':
        """Open the closed file and use the correct wrapper class

        Parameters
        ----------
        filename: str ot pathlib.Path
            Path to file to be opened
        mode: str
            Mode used to open the file: r, r+, w, w-, x, a

        Returns
        -------
        Subclass of File
        """
        return File(filename, mode)

    def dump_jsonld(self,
                    skipND: int = 1,
                    structural: bool = True,
                    semantic: bool = True,
                    resolve_keys: bool = True,
                    blank_node_iri_base: Optional[str] = None,
                    **kwargs) -> str:
        """Dump the file content as JSON-LD string"""
        return self.serialize(fmt="json-ld",
                              skipND=skipND,
                              structural=structural,
                              semantic=semantic,
                              resolve_keys=resolve_keys,
                              blank_node_iri_base=blank_node_iri_base,
                              **kwargs)

    def serialize(self, fmt: str,
                  skipND: int = 1,
                  structural: bool = True,
                  contextual: bool = True,
                  blank_node_iri_base: Optional[str] = None,
                  context: Optional[Dict] = None,
                  indent: int = 2,
                  **kwargs
                  ):
        """Serialize the file content to a specific format"""
        from h5rdmtoolbox.ld.utils import optimize_context
        from h5rdmtoolbox.ld import get_ld
        fmt = kwargs.pop("format", fmt)

        graph = get_ld(self.hdf_filename,
                       structural=structural,
                       contextual=contextual,
                       blank_node_iri_base=blank_node_iri_base,
                       skipND=skipND,
                       **kwargs)
        context = context or {}
        context = optimize_context(graph, context)
        return graph.serialize(format=fmt,
                               indent=indent,
                               auto_compact=True,
                               context=context)


Dataset._h5grp = Group
Dataset._h5ds = Dataset

Group._h5grp = Group
Group._h5ds = Dataset
