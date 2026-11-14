"""HDF5 groups, metadata and dataset creation."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
from collections.abc import Iterable
from pathlib import Path
from datetime import datetime
import json
import os
import pathlib
import warnings

import h5py
import numpy as np
from h5py._hl.base import phil
import rdflib
import xarray as xr

from .._repr import H5PY_SPECIAL_ATTRIBUTES, H5Repr
from .h5attr import H5_DIM_ATTRS, WrapperAttributeManager
from .h5utils import _is_not_valid_natural_name, get_rootparent
from .. import consts, protocols
from .._cfg import get_config
from ..ld import rdf
from ._shared import Lower, _delattr, _normalize_time_format, assert_filename_existence, logger
from ..science import xarray_io  # registers the xarray HDF accessor


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
    def decode_calibration(self):
        """Whether scientific reads apply the attached scale and offset."""
        return self.__dict__.get('_decode_calibration', False)

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
    def parent(self):
        """Return the parent with the same scientific read policy."""
        return self._h5grp(super().parent)

    @property
    def rootparent(self):
        """Return the root group instance."""
        from .file import File
        if self.name == "/":
            return File(self._id, decode_calibration=self.decode_calibration)
        return File(get_rootparent(self.parent)._id, decode_calibration=self.decode_calibration)

    rootgroup = rootparent  # alias

    @property
    def basename(self) -> str:
        """Basename of dataset (path without leading forward slash)"""
        return os.path.basename(self.name)

    def get_datasets(
        self, pattern: str = ".*", recursive: bool = False
    ) -> List[h5py.Dataset]:
        """Return list of datasets in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the datasets."""
        if pattern == ".*" and not recursive:
            return [v for v in self.values() if isinstance(v, h5py.Dataset)]
        return [
            self.rootparent[ds.name]
            for ds in self.find(
                {"$name": {"$regex": pattern}}, "$Dataset", recursive=recursive
            )
        ]

    def get_groups(
        self, pattern: str = ".*", recursive: bool = False
    ) -> List[h5py.Group]:
        """Return list of groups in the current group.
        If pattern is None, all groups are returned.
        If pattern is not None a regrex-match is performed
        on the basenames of the groups."""
        if pattern == ".*" and not recursive:
            return [v for v in self.values() if isinstance(v, h5py.Group)]
        # if return_lazy:
        #     return self.find({'$name': {'$regex': pattern}}, '$Group', recursive=recursive)
        return [
            self.rootparent[g.name]
            for g in self.find(
                {"$name": {"$regex": pattern}}, "$Group", recursive=recursive
            )
        ]

    def __init__(self, _id, *, decode_calibration=None):
        if isinstance(_id, h5py.Group):
            _id = _id.id
        if isinstance(_id, h5py.h5g.GroupID):
            super().__init__(_id)
        else:
            raise ValueError(
                "Could not initialize Group. A h5py.h5f.FileID object must be passed"
            )
        self._decode_calibration = self.__dict__.get("_decode_calibration", False) if decode_calibration is None else bool(decode_calibration)
        self._hdf_filename = Path(self.file.filename)

    def __setitem__(
        self, name: str, obj: Union[xr.DataArray, List, Tuple, Dict, h5py.ExternalLink]
    ) -> protocols.H5TbxDataset:
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
            return self._h5ds(obj.hdf.to_group(self, name).id)
        if isinstance(obj, (list, tuple)):
            if not isinstance(obj[1], dict):
                raise TypeError(f"Second item must be type dict but is {type(obj[1])}")
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

    def values(self):
        """Yield wrapped group/dataset objects."""
        for key in self.keys():
            yield self[key]

    def items(self):
        """Yield `(name, wrapped-object)` pairs."""
        for key in self.keys():
            yield key, self[key]

    def visititems(self, func):
        """Visit wrapped objects to keep wrapper APIs available in callbacks."""
        def _visitor(name):
            return func(name, self[name])

        return super().visit(_visitor)

    def __getattr__(self, item: str):

        try:
            return super().__getattribute__(item)
        except (RuntimeError, AttributeError) as e:
            if not get_config("natural_naming"):
                # raise an error if natural naming is NOT enabled
                raise AttributeError(e)

        # if item in self.__dict__:
        #     return super().__getattribute__(item)
        try:
            _item = item.replace("_", " ")
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
        super().__setattr__(key, value)

    def __str__(self) -> str:
        return f'<HDF5 wrapper group "{self.name}" (members: {len(self)})>'

    def __repr__(self) -> str:
        return self.__str__()

    def __lt__(self, other):
        return self.name < other.name

    def __delattr__(self, item):
        _delattr(self, item)



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
        warnings.warn(
            'Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning
        )
        return rdf.RDFManager(self.attrs)


    def get_tree_structure(
        self, recursive=True, ignore_attrs: List[str] = None
    ) -> Dict:
        """Return the tree (attributes, names, shapes) of the group and subgroups.

        The structure uses '/' as the key for root attributes, with child groups and
        datasets as sibling keys at the same level.

        Returns
        -------
        Dict
            Dictionary with '/' containing root attributes, and other keys for
            groups/datasets. Groups contain nested dictionaries with the same structure.
        """
        if ignore_attrs is None:
            ignore_attrs = H5PY_SPECIAL_ATTRIBUTES
        tree: Dict = {"/": {}}
        for ak, av in self.attrs.items():
            if ak not in H5_DIM_ATTRS and ak not in ignore_attrs:
                tree["/"][ak] = av
        for k, v in self.items():
            if isinstance(v, h5py.Dataset):
                ds_dict: Dict = {"shape": v.shape, "ndim": v.ndim}
                for ak, av in v.attrs.items():
                    if ak not in H5_DIM_ATTRS and ak not in ignore_attrs:
                        ds_dict[ak] = av
                tree[k] = ds_dict
            elif isinstance(v, h5py.Group) and recursive:
                tree[k] = v.get_tree_structure(recursive, ignore_attrs)
        return tree

    def create_group(
        self,
        name: str,
        overwrite: bool = None,
        attrs: Dict = None,
        rdf_type: Optional[Union[str, rdflib.URIRef]] = None,
        rdf_subject: Optional[Union[str, rdflib.URIRef]] = None,
        update_attrs: Optional[bool] = False,
        track_order=None,
        **kwargs,
    ) -> "Group":
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

        attrs = dict(attrs)
        if name in self:
            if not isinstance(self[name], h5py.Group):
                raise ValueError("The name you passed is already used for a dataset!")

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

        if _is_not_valid_natural_name(self, name, get_config("natural_naming")):
            raise ValueError(
                f'The group name "{name}" is not valid. It is an '
                f"attribute of the class and cannot be used "
                f"while natural naming is enabled"
            )

        subgrp = super().create_group(name, track_order=track_order)

        # new_subgroup = h5py.Group.create_group(self, name, track_order=track_order)
        logger.debug(f'Created group "{name}" at "{self.name}"-level.')

        h5tbxgrp = self._h5grp(subgrp)
        if attrs:
            for k, v in attrs.items():
                h5tbxgrp.attrs[k] = v
        if rdf_type is not None:
            h5tbxgrp.rdf.type = rdf_type
        if rdf_subject:
            h5tbxgrp.rdf.subject = rdf_subject
        return h5tbxgrp

    def create_time_dataset(
        self,
        name: str,
        data: Union[datetime, List],
        time_format: str,
        assign_rdf: bool = True,
        overwrite: bool = False,
        attrs: Dict = None,
        **kwargs,
    ):
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
        time_format = _normalize_time_format(time_format)

        attrs.update({"time_format": time_format})

        if isinstance(data, np.ndarray):
            ds = self.create_string_dataset(
                name,
                data=[t.astype(datetime).strftime(time_format) for t in data],
                overwrite=overwrite,
                attrs=attrs,
                **kwargs,
            )
        else:
            _data = np.asarray(data)
            _orig_shape = _data.shape
            _flat_data = _data.flatten()
            _flat_data = np.asarray([t.strftime(time_format) for t in _flat_data])
            _reshaped_data = _flat_data.reshape(_orig_shape)
            ds = self.create_string_dataset(
                name,
                data=_reshaped_data.tolist(),
                overwrite=overwrite,
                attrs=attrs,
                **kwargs,
            )
        if assign_rdf:
            ds.rdf.type = "https://schema.org/DateTime"
            ds.rdf["time_format"].predicate = (
                "https://matthiasprobst.github.io/pivmeta#timeFormat"
            )
        return ds

    def create_string_dataset(
        self,
        name: str,
        data: Union[str, List[str]],
        overwrite=False,
        attrs=None,
        rdf_type: Optional[Union[str, rdflib.URIRef]] = None,
        **kwargs,
    ):
        """Create a string dataset. In this version only one string is allowed.
        In future version a list of strings may be allowed, too.
        No long or standard name needed"""

        if attrs is None:
            attrs = {}

        attrs = dict(attrs)

        if isinstance(data, str):
            n_letter = len(data)
        elif isinstance(data, (tuple, list)):
            n_letter = max([len(d) for d in np.asarray(data).flatten()])
        else:
            raise TypeError(
                f'Unexpected type for parameter "data": {type(data)}. Expected str or List/Tuple of str'
            )
        dtype = f"S{max(1, n_letter)}"
        if name in self:
            if overwrite is True:
                del self[name]  # delete existing dataset
            # else let h5py return the error

        if isinstance(data, str):
            compression = None
            compression_opts = None
        else:
            compression = kwargs.pop("compression", get_config("hdf_compression"))
            compression_opts = kwargs.pop(
                "compression_opts", get_config("hdf_compression_opts")
            )

        make_scale = kwargs.pop("make_scale", False)
        ds = super().create_dataset(
            name,
            dtype=dtype,
            data=data,
            **kwargs,
            compression=compression,
            compression_opts=compression_opts,
        )
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

    def create_dataset(
        self,
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
        **kwargs,
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
            Additional keyword arguments that are passed
            to the parent function.
            For **kwargs, see h5py.File.create_dataset.

            Metadata belongs in attrs; additional keywords are passed to h5py.

        Returns
        -------
        ds : h5py.Dataset
            created dataset
        """

        if isinstance(data, str):
            if attach_data_scale is not None or attach_data_offset is not None:
                raise ValueError(
                    "Cannot set data_scale or data_offset for string datasets."
                )
            return self.create_string_dataset(
                name=name,
                data=data,
                overwrite=overwrite,
                attrs=attrs,
                rdf_type=rdf_type,
                **kwargs,
            )
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
            attach_scales = kwargs.pop("attach_scale", None)

        if attach_scales is not None:
            if not isinstance(attach_scales, (list, tuple)):
                attach_scales = (attach_scales,)
            if any([True for a in attach_scales if a]) and make_scale:
                raise ValueError("Cannot make scale and attach scale at the same time!")

        attrs = dict(attrs)

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
        compression = kwargs.pop("compression", get_config("hdf_compression"))
        compression_opts = kwargs.pop(
            "compression_opts", get_config("hdf_compression_opts")
        )

        if shape is not None:
            if len(shape) == 0:
                compression, compression_opts, chunks = None, None, None

        if name:
            if _is_not_valid_natural_name(self, name, get_config("natural_naming")):
                raise ValueError(
                    f'The dataset name "{name}" is not a valid. It is an '
                    f"attribute of the class and cannot be used "
                    f"while natural naming is enabled"
                )

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
                        raise TypeError(
                            f"Expecting type string or a h5py.Dataset for scale, not {type(scale)}"
                        )
                    data = data.rename({dim: scale_name}).assign_coords(
                        {scale_name: scale_data}
                    )
            attrs.update(data.attrs)
            xrds = data.hdf.to_group(
                self._h5grp(self),
                name=name,
                overwrite=overwrite,
                compression=compression,
                compression_opts=compression_opts,
                attrs=attrs,
            )
            return self._h5ds(xrds.id)

        if not isinstance(make_scale, (bool, str)):
            raise TypeError(
                f"Make scale must be a boolean or a string not {type(make_scale)}"
            )

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
                    raise TypeError(
                        f"Expected ancillary dataset to be of type h5py.Dataset, "
                        f"but got {type(anc_ds)}"
                    )
                if anc_ds.shape != _data.shape:
                    raise ValueError(
                        f"Associated dataset {anc_name} has shape {anc_ds.shape} "
                        f"which does not match dataset shape {_data.shape}"
                    )
            attrs[consts.ANCILLARY_DATASET] = json.dumps(
                {k: v.name for k, v in ancillary_datasets.items()}
            )

        _maxshape = kwargs.get("maxshape", shape)

        logger.debug(
            f'Creating dataset "{name}" in "{self.name}" with maxshape "{_maxshape}" '
            f'and using compression "{compression}" with opt "{compression_opts}"'
        )

        # if possible, create dataset with shape first:
        if _data is not None:
            if _data.ndim == 0:
                # create 0D dataset
                _ds = super().create_dataset(
                    name, shape=shape, dtype=dtype, data=_data, **kwargs
                )
            else:
                # create ND dataset with shape, data is assigned later
                _ds = super().create_dataset(
                    name,
                    shape=shape,
                    dtype=dtype,
                    data=_data,
                    chunks=chunks,
                    compression=compression,
                    compression_opts=compression_opts,
                    **kwargs,
                )
        else:
            # no data given, initialize with shape only
            _ds = super().create_dataset(
                name,
                shape=shape,
                dtype=dtype,
                data=_data,
                compression=compression,
                compression_opts=compression_opts,
                chunks=chunks,
                **kwargs,
            )

        ds = self._h5ds(_ds.id)

        if rdf_type is not None:
            ds.rdf.type = rdf_type

        if attach_data_scale is not None or attach_data_offset is not None:
            units = attrs.get("units", None)
            if units:
                ds.attrs["units"] = units
            ds.attach_data_scale_and_offset(attach_data_scale, attach_data_offset)

        # assign attributes, which may raise errors if attributes are standardized and not fulfill requirements:
        if attrs:
            for k, v in attrs.items():
                if isinstance(v, h5py.Dataset):
                    ds.attrs.__setitem__(k, v.name, attrs)
                else:
                    ds.attrs.__setitem__(k, v, attrs)

        # what is this for? uncommented it in version v1.0.1
        # if isinstance(data, np.ndarray):
        #     if data is not None and data.ndim > 0:
        #         ds[()] = data

        # make scale
        if make_scale:
            if isinstance(make_scale, bool):
                ds.make_scale("")
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
                            raise ValueError(
                                f"Cannot only attach 1D datasets, but got "
                                f"{ds_to_attach.ndim}D dataset {ds_to_attach.name}"
                            )
                        if not shape_of_axis_i == ds_to_attach.shape[0]:
                            del self[ds.name]
                            raise ValueError(
                                f"Cannot assign {ds_to_attach.name} to {name} because it has "
                                f"different shape {ds_to_attach.shape[0]} than {shape_of_axis_i}"
                            )
                        ds.dims[i].attach_scale(ds_to_attach)
        return ds

    def find_one(
        self,
        flt: Union[Dict, str],
        objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
        recursive: bool = True,
        ignore_attribute_error: bool = False,
    ) -> protocols.LazyObject:
        """See ObjDB.find_one()"""
        from h5rdmtoolbox.database import ObjDB

        return ObjDB(self).find_one(flt, objfilter, recursive, ignore_attribute_error)

    def find(
        self,
        flt: Union[Dict, str, List[str]],
        objfilter: Union[str, h5py.Dataset, h5py.Group, None] = None,
        recursive: bool = True,
        ignore_attribute_error: bool = False,
    ) -> List[protocols.LazyObject]:
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

        return ObjDB(self).find(
            flt,
            objfilter,
            recursive=recursive,
            ignore_attribute_error=ignore_attribute_error,
        )



    def create_dataset_from_image(
        self,
        img_data: Union[Iterable, np.ndarray, List[np.ndarray]],
        name,
        chunks=None,
        dtype=None,
        axis=0,
        **kwargs,
    ):
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
        _compression, _compression_opts = (
            get_config("hdf_compression"),
            get_config("hdf_compression_opts"),
        )
        compression = kwargs.pop("compression", _compression)
        compression_opts = kwargs.pop("compression_opts", _compression_opts)
        first_image = None
        n = None

        if axis not in (0, -1):
            raise ValueError(
                f"Parameter for parameter axis can only be 0 or 1 but not {axis}"
            )

        iterable: bool = isinstance(img_data, Iterable)
        if iterable:
            # check if img_data has method __len__():
            if not hasattr(img_data, "__len__"):
                raise ValueError("img_data must have method __len__()")
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

        ds = self.create_dataset(
            name=name,
            shape=shape,
            compression=compression,
            compression_opts=compression_opts,
            chunks=chunks,
            dtype=dtype,
            **kwargs,
        )
        if isinstance(img_data, np.ndarray):
            ds[()] = img_data
            return ds

        assert first_image is not None, "First image is None. This should not happen!"
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
            ds = self.create_dataset(
                str(coord),
                data=dataset.coords[coord].values,
                attrs=dataset.coords[coord].attrs,
                overwrite=False,
            )
            ds.make_scale()
            ds_coords[coord] = ds
        for data_var in dataset.data_vars.keys():
            ds = self.create_dataset(
                data_var,
                data=dataset[data_var].values,
                attrs=dataset[data_var].attrs,
                overwrite=False,
            )
            for idim, dim in enumerate(dataset[data_var].dims):
                if dim not in ds_coords:
                    # xarray does not let me add attributes to this dimension
                    h5py.Group(self.id).create_dataset(
                        name=dim, data=dataset[data_var][dim].values
                    )
                    ds_coords[dim] = ds
                else:
                    ds.dims[idim].attach_scale(ds_coords[dim])

    def create_external_link(
        self, name, filename, path, overwrite=False, keep_relative=False
    ):
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
        logger.debug(
            f'Trying to create external link group with name "{name}". Source is filename="{filename}" and '
            f'path="{path}". Overwrite is set to {overwrite} and keep_relative to {keep_relative}'
        )
        if not keep_relative:
            filename = os.path.abspath(filename)
        if name in self:
            if overwrite:
                del self[name]
                self[name] = h5py.ExternalLink(filename, path)
                return self[name]
            logger.debug(
                "External link %s was not created. A Dataset with this name"
                " already exists and overwrite is set to False! "
                "You can pass overwrite=True in order to overwrite the "
                "existing dataset",
                name,
            )
            raise ValueError(
                f"External link {name} was not created. A Dataset with this name"
                " already exists and overwrite is set to False! "
                "You can pass overwrite=True in order to overwrite the "
                "existing dataset"
            )
        self[name] = h5py.ExternalLink(filename, path)
        return self[name]



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

    def dump(
        self,
        collapsed: bool = True,
        max_attr_length: Union[int, None] = None,
        chunks: bool = False,
        maxshape: bool = False,
    ) -> None:
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
        return self.hdfrepr.__html__(
            self, collapsed=collapsed, chunks=chunks, maxshape=maxshape
        )

    def _repr_html_(self):
        return self.hdfrepr.__html__(self)

    def sdump(self, hide_uri: bool = False):
        """string representation of group"""
        return self.hdfrepr.str_repr(self, hide_uri=hide_uri)

    dumps = sdump

    def _h5grp(self, obj):
        from .group import Group
        return Group(obj, decode_calibration=self.decode_calibration)

    def _h5ds(self, obj):
        from .dataset import Dataset
        return Dataset(obj, decode_calibration=self.decode_calibration)
