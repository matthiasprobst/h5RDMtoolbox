"""HDF5 datasets, coordinates and scientific reads."""
from __future__ import annotations

from typing import Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
import os
import pathlib
import warnings

import h5py
import numpy as np
from h5py._hl.base import phil, with_phil
import xarray as xr

from .h5attr import WrapperAttributeManager, pop_hdf_attributes
from .. import _repr, consts, protected_attributes, protocols
from ..science.calibration import dataset_value_decoder
from .._cfg import get_config, get_ureg
from ..ld import rdf
from ._shared import (
    DatasetValues,
    _delattr,
    _normalize_time_format,
    assert_filename_existence,
    convert_strings_to_datetimes,
    logger,
    only_0d_and_1d,
)


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
            raise ValueError("Can only compare to floats and integers!")
        data = self.values[()]
        if data.ndim == 1:
            return np.where(data <= other)[0]
        return data <= other

    @only_0d_and_1d
    def __gt__(self, other: Union[int, float]):
        if not isinstance(other, (int, float)):
            raise ValueError("Can only compare to floats and integers!")
        data = self.values[()]
        if data.ndim == 1:
            return np.where(data > other)[0]
        return data > other

    @only_0d_and_1d
    def __ge__(self, other: Union[int, float]):
        if not isinstance(other, (int, float)):
            raise ValueError("Can only compare to floats and integers!")
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
    def decode_calibration(self):
        """Whether scientific reads apply the attached scale and offset."""
        return self.__dict__.get('_decode_calibration', False)

    @property
    def rdf(self):
        """Return RDF Manager"""
        return rdf.RDFManager(self.attrs)

    @property
    def iri(self):
        """Deprecated. Use rdf instead."""
        warnings.warn(
            'Property "iri" is deprecated. Use "rdf" instead.', DeprecationWarning
        )
        return rdf.RDFManager(self.attrs)

    @property
    def hdf_filename(self) -> pathlib.Path:
        """The filename of the file, even if the HDF5 file is closed."""
        return assert_filename_existence(self._hdf_filename)

    @property
    def attrs(self) -> protocols.H5TbxAttributeManager:
        """Exact copy of parent class:
        Attributes attached to this object"""
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
            return self._h5ds(source)

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
            raise ValueError(
                "Shape of flag dataset does not match the shape of the current dataset!"
            )
        ancillary_datasets = self.ancillary_datasets
        ancillary_datasets[ancillary_dataset.basename] = ancillary_dataset.name
        self.attrs[consts.ANCILLARY_DATASET] = ancillary_datasets
        return self

    def detach_data_scale(self):
        """Remove the attached data scale dataset from this dataset."""
        warnings.warn(
            "Note, that detaching data scale may influence the correctness and traceability of your data",
            UserWarning,
        )
        self.attrs.pop("DATA_SCALE", None)

    def detach_data_offset(self):
        """Remove the attached data offset dataset from this dataset."""
        warnings.warn(
            "Note, that detaching data offset may influence the correctness and traceability of your data",
            UserWarning,
        )
        self.attrs.pop("DATA_OFFSET", None)

    def attach_data_scale_and_offset(
        self, scale: Union[None, h5py.Dataset], offset: Union[None, h5py.Dataset]
    ):
        """Attach a data scale and offset to this dataset. The scale and offset must have the same"""
        if self.attrs.get("IS_DATA_SCALE", False):
            raise ValueError(
                "Cannot attach data scale to a dataset, which is already a data scale!"
            )
        if self.attrs.get("IS_DATA_OFFSET", False):
            raise ValueError(
                "Cannot attach data offset to a dataset, which is already a data offset!"
            )
        if "units" not in self.attrs:
            raise ValueError(
                'Cannot attach data scale if no attribute "units" is not set!'
            )

        this_units = get_ureg().Unit(self.attrs.get("units", ""))

        # try:
        if scale is not None:
            scaled_units = this_units * get_ureg().Unit(scale.attrs.get("units", ""))
        else:
            scaled_units = this_units

        if offset is not None:
            if (
                scaled_units.dimensionality
                == get_ureg().Unit(offset.attrs.get("units", "")).dimensionality
            ):
                pass
            else:
                raise ValueError("Units of scale and offset must be compatible!")

        if scale is not None:
            self.attrs["DATA_SCALE"] = scale.name
        if offset is not None:
            self.attrs["DATA_OFFSET"] = offset.name

    def get_data_scale(self):
        """Return the data scale dataset if attached to this dataset."""
        if "DATA_SCALE" in self.attrs:
            _src = self.attrs["DATA_SCALE"]
            if isinstance(_src, str):
                return self.rootparent[_src]
            return self.rootparent[self.attrs["DATA_SCALE"].name]
        return None

    def get_data_offset(self):
        """Return the data offset dataset if attached to this dataset."""
        if "DATA_OFFSET" in self.attrs:
            _src = self.attrs["DATA_OFFSET"]
            if isinstance(_src, str):
                return self.rootparent[_src]
            return self.rootparent[self.attrs["DATA_OFFSET"].name]
        return None

    @property
    def coords(self) -> Dict:
        """Return a dictionary of the dimension scales of the dataset.
        Corresponds to the xarray coordinates."""
        coords = {}
        for dim in self.dims:
            if len(dim) > 0:
                for i, d in enumerate(dim):
                    coords[dim[i].name.rsplit("/")[-1]] = dim[i]
        return coords
        # return {d[0].name.rsplit('/')[-1]: d[0] for d in self.dims if len(d) > 0}

    def assign_coord(self, coord):
        if isinstance(coord, str):
            if coord not in self.rootparent:
                raise ValueError(f"Coordinate {coord} not found in the file!")
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
                    raise KeyError(
                        f"Coordinate {cname} not in {list(ds_coords.keys())}"
                    )

            sl = {
                cname: slice(None)
                for cname, _ in zip(ds_coords.keys(), range(self.ndim))
            }
            sl_key_list = list(sl.keys())
            for (cname, item), _ in zip(indexers.items(), range(self.ndim)):
                # if the indexer name is in the same dimension as one of the already registered
                # coordinates in "sl", then replace
                _replaced = False
                for idim, d in enumerate(self.dims):
                    for i in range(len(d)):
                        if d[i].name.rsplit("/")[-1] == cname:
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
            if not all([cname.startswith("dim_") for cname in indexers.keys()]):
                raise KeyError(f"No coordinates available. Provide dim_<i> as key!")
            dim_dict = {f"dim_{i}": slice(None) for i in range(len(self.shape))}
            # indices = [int(cname.split('_')[1]) for cname in indexers.keys()]
            sl = {
                cname: slice(None)
                for cname, _ in zip(dim_dict.keys(), range(self.ndim))
            }
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
                raise KeyError(
                    f"Coordinate {coord_name} not in {list(av_coord_datasets.keys())}"
                )
            sel_coord_data = av_coord_datasets[coord_name][()]
            if method is None or method == "exact":
                idx = np.where(sel_coord_data == coord_values)[0]

                if idx.size == 0:
                    raise ValueError(
                        f"No matching coordinate found for coordinate {coord_name} and value {coord_values}. "
                        f'Consider using method "nearest".'
                    )
                if len(idx) == 1:
                    idx = int(idx[0])

            elif method == "nearest":
                # idx = (sel_coord_data - coord_values).argmin()[()]
                # print(idx)
                if not isinstance(coord_values, (int, float)):
                    _coord_values = np.array(coord_values)
                    if _coord_values.ndim != 1:
                        raise NotImplementedError(
                            "Cuurently .sel() only allows 0D or 1D data for coord_values"
                        )
                    _absmins = [np.abs(sel_coord_data - cv) for cv in coord_values]
                    idx = [int(np.argmin(_absmin)) for _absmin in _absmins]
                else:
                    _absmin = np.abs(sel_coord_data - coord_values)
                    idx = int(np.argmin(_absmin))
            else:
                raise NotImplementedError(
                    "Only exact and nearest match method implemented"
                )
            isel[coord_name] = idx
        return self.isel(**isel)

    def __getattr__(self, item):

        if item not in self.__dict__:
            for d in self.dims:
                if len(d) > 0:
                    for i in range(len(d)):
                        if item == os.path.basename(d[i].name):
                            return self._h5ds(d[i])
        return super().__getattribute__(item)

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if isinstance(value, xr.DataArray):
            self.attrs.update(value.attrs)
            super().__setitem__(key, value.data)
        else:
            super().__setitem__(key, value)

    @dataset_value_decoder
    def __getitem__(
        self, args, new_dtype=None, nparray=False, links_as_strings: bool = False
    ) -> Union[xr.DataArray, np.ndarray]:
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

        if not get_config("return_xarray") or nparray:
            return super().__getitem__(args, new_dtype=new_dtype)

        # check if any entry in args is of type Ellipsis:
        if any(arg is Ellipsis for arg in args):
            # substitute Ellipsis with as many slices as needed:
            args = list(args)
            ellipsis_index = args.index(Ellipsis)
            args.pop(ellipsis_index)
            args[ellipsis_index:ellipsis_index] = [
                slice(None) for _ in range(self.ndim - len(args))
            ]
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

        if "DIMENSION_LIST" in ds_attrs:
            # there are coordinates to attach...

            myargs = [slice(None) for _ in range(self.ndim)]
            for ia, a in enumerate(args):
                myargs[ia] = a

            # remember the first dimension name for all axis:
            dims_names = [
                d[0].name.rsplit("/")[-1] if len(d) > 0 else f"dim_{ii}"
                for ii, d in enumerate(self.dims)
            ]

            coords = {}

            for dim, dim_name, arg in zip(self.dims, dims_names, myargs):
                for iax, _ in enumerate(dim):
                    dim_ds = dim[iax]
                    coord_name = dim[iax].name.rsplit("/")[-1]
                    if dim_ds.ndim == 0:
                        dim_ds_data = dim_ds[()]
                    else:
                        dim_ds_data = dim_ds[arg]
                    dim_ds_attrs = pop_hdf_attributes(dim_ds.attrs)
                    if dim_ds_data.dtype.kind == "S":
                        # decode string array
                        if dim_ds_attrs.get("time_format", False):
                            _time_format = _normalize_time_format(
                                dim_ds_attrs["time_format"]
                            )
                            if dim_ds_data.ndim == 0:
                                dim_ds_data = np.array(
                                    datetime.strptime(
                                        dim_ds_data.astype(str),
                                        _time_format,
                                    )
                                ).astype(datetime)
                            else:
                                dim_ds_data = convert_strings_to_datetimes(
                                    dim_ds_data.astype(str),
                                    time_format=_time_format,
                                )
                                # dim_ds_data = np.array(
                                #     [datetime.fromisoformat(t) for t in dim_ds_data.astype(str)]).astype(
                                #     datetime)
                    if dim_ds_data.ndim == 0:
                        if isinstance(arg, int):
                            coords[coord_name] = xr.DataArray(
                                name=coord_name,
                                dims=(),
                                data=dim_ds_data,
                                attrs=dim_ds_attrs,
                            )
                        else:
                            coords[coord_name] = xr.DataArray(
                                name=coord_name,
                                dims=coord_name,
                                data=[
                                    dim_ds[()],
                                ],
                                attrs=dim_ds_attrs,
                            )
                    else:
                        if isinstance(dim_ds_data, np.ndarray):
                            coords[coord_name] = xr.DataArray(
                                name=coord_name,
                                dims=dim_name,
                                data=dim_ds_data,
                                attrs=dim_ds_attrs,
                            )
                        else:
                            coords[coord_name] = xr.DataArray(
                                name=coord_name,
                                dims=(),
                                data=dim_ds_data,
                                attrs=dim_ds_attrs,
                            )

            used_dims = [
                dim_name
                for arg, dim_name in zip(myargs, dims_names)
                if isinstance(arg, (slice, np.ndarray, list))
            ]

            coordinates: Optional[Union[str, List[str]]] = ds_attrs.get(
                protected_attributes.COORDINATES
            )
            if coordinates is not None:
                if isinstance(coordinates, str):
                    coordinates = [
                        coordinates,
                    ]
                else:
                    coordinates = list(coordinates)

                for c in coordinates:
                    if c[0] == "/":
                        _data = self.rootparent[c]
                    else:
                        _data = self.parent[c]
                    _name = Path(c).stem
                    coords.update(
                        {
                            _name: xr.DataArray(
                                name=_name,
                                dims=(),
                                data=_data,
                                attrs=pop_hdf_attributes(self.parent[c].attrs),
                            )
                        }
                    )
            return xr.DataArray(
                name=Path(self.name).stem,
                data=arr,
                dims=used_dims,
                coords=coords,
                attrs=attrs,
            )
        # check if arr is string
        if self.dtype == "object":
            pass
        elif arr.dtype.kind == "S":
            # decode string array
            try:
                _arr = arr.astype(str)
            except UnicodeDecodeError:
                return xr.DataArray(arr, attrs=attrs)

            time_format = self.attrs.get("time_format", None)
            if time_format is not None:
                time_format = _normalize_time_format(time_format)
                if _arr.ndim == 0:
                    _arr = np.asarray(datetime.strptime(_arr, time_format))
                elif _arr.ndim == 1:
                    _arr = [datetime.strptime(str(t), time_format) for t in _arr]
                else:  # _arr.ndim > 1:
                    orig_shape = _arr.shape
                    _flat_arr = np.asarray(
                        [datetime.strptime(t, time_format) for t in _arr.flatten()]
                    )
                    _arr = _flat_arr.reshape(orig_shape)
                return xr.DataArray(_arr, attrs=attrs)

            if isinstance(_arr, np.ndarray):
                return xr.DataArray(_arr, attrs=attrs)
            return _arr

        coords = {}
        coordinates: Optional[Union[str, List[str]]] = ds_attrs.get(
            protected_attributes.COORDINATES, None
        )
        if coordinates is not None:
            if isinstance(coordinates, str):
                coordinates = [
                    coordinates,
                ]
            else:
                coordinates = list(coordinates)

            for c in coordinates:
                if c[0] == "/":
                    _data = self.rootparent[c]
                else:
                    _data = self.parent[c]
                _name = Path(c).stem
                coords.update(
                    {
                        _name: xr.DataArray(
                            name=_name,
                            dims=(),
                            data=_data,
                            attrs=pop_hdf_attributes(self.parent[c].attrs),
                        )
                    }
                )
            da = xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)
            for k, v in coords.items():
                da = da.assign_coords({k: v})
            return da
        return xr.DataArray(name=Path(self.name).stem, data=arr, attrs=attrs)

    def __repr__(self):
        return super().__repr__()

    def dump(self) -> None:
        """Call sdump()"""
        self.sdump()

    def sdump(self) -> None:
        """Print the dataset content in a more comprehensive way"""
        out = f'{self.__class__.__name__} "{self.name}"'
        out += f"\n{'-' * len(out)}"
        out += f"\n{'*shape:':14} {self.shape}"
        out += f"\n{'*dtype:':14} {self.dtype}"
        out += f"\n{'*compression:':14} {self.compression} ({self.compression_opts})"

        for k, v in self.attrs.items():
            out += f"\n{k + ':':14} {v}"

        has_dim = False
        dim_str = "\n\nDimensions"
        for _id, d in enumerate(self.dims):
            naxis = len(d)
            if naxis > 0:
                has_dim = True
                for iaxis in range(naxis):
                    if naxis > 1:
                        dim_str += f"\n   [{_id}({iaxis})] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}"
                    else:
                        dim_str += f"\n   [{_id}] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}"
        if has_dim:
            out += dim_str
        print(out)

    dumps = sdump

    def __init__(self, _id, *, decode_calibration=None):
        if isinstance(_id, h5py.Dataset):
            _id = _id.id
        if isinstance(_id, h5py.h5d.DatasetID):
            super().__init__(_id)
        else:
            raise ValueError(
                f"Could not initialize Dataset with type(_id)={type(_id)}. "
                "A h5py.h5f.FileID object must be passed"
            )

        super().__init__(_id)
        self._decode_calibration = self.__dict__.get("_decode_calibration", False) if decode_calibration is None else bool(decode_calibration)
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
                f'The target scale index "iscale" is out of range [0, {nscales - 1}]'
            )
        backup_scales = self.dims[axis].items()
        for _, ds in backup_scales:
            self.dims[axis].detach_scale(ds)
        ils = [iscale, *[i for i in range(nscales) if i != iscale]]
        for i in ils:
            self.dims[axis].attach_scale(backup_scales[i][1])
        logger.debug("new primary scale: %s", self.dims[axis][0])

    def _h5grp(self, obj):
        from .group import Group
        return Group(obj, decode_calibration=self.decode_calibration)

    def _h5ds(self, obj):
        from .dataset import Dataset
        return Dataset(obj, decode_calibration=self.decode_calibration)
