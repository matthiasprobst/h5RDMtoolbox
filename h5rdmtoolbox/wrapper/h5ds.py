import logging
import os
import warnings
from pathlib import Path
from typing import Union

import h5py
import numpy as np
# noinspection PyUnresolvedReferences
import pint_xarray
import xarray as xr
from h5py._hl.base import phil

# noinspection PyUnresolvedReferences
from . import xr2hdf
from .h5attr import WrapperAttributeManager, pop_hdf_attributes
from .. import _repr
from .. import config

logger = logging.getLogger(__package__)


class DatasetValues:
    """helper class to work around xarray"""

    def __init__(self, h5dataset):
        self.h5dataset = h5dataset

    def __getitem__(self, args, new_dtype=None):
        return self.h5dataset.__getitem__(args, new_dtype=new_dtype, nparray=True)

    def __setitem__(self, args, val):
        return self.h5dataset.__setitem__(args, val)


class H5Dataset(h5py.Dataset):
    """Subclass of h5py.Dataset implementing a model.
    This core version enforces the user to use units and
    long_name or standard_name when creating datasets.
    The property standard_name return a standard name
    model.
    """

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

        def get_root(parent):
            global found
            found = parent.parent

            def search(parent):
                global found
                parent = parent.parent
                if parent.name == '/':
                    found = parent
                else:
                    _ = search(parent)

            search(parent)
            return found

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
            Helper class mimicing the h5py behaviour of returning a numpy array.
        """
        return DatasetValues(self)

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
        behaviour of the h5p-package is used and a np.ndarray is returend.
        Note, that even if `RETURN_XARRAY` is True, there is another way to
        receive  numpy array. This is by calling .values[:] on the dataset."""
        args = args if isinstance(args, tuple) else (args,)
        if not config.RETURN_XARRAY or nparray:
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

    def __str__(self):
        return f'<HDF5 wrapper dataset shape "{self.shape}" (<{self.dtype}>)>'

    def __repr__(self) -> str:
        return self.__str__()

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
        out += f'\n{"long_name:":14} {self.long_name}'
        out += f'\n{"standard_name:":14} {self.attrs.get("standard_name")}'
        out += f'\n{"units:":14} {self.units}'

        has_dim = False
        dim_str = f'\n\nDimensions'
        for _id, d in enumerate(self.dims):
            naxis = len(d)
            if naxis > 0:
                has_dim = True
                for iaxis in range(naxis):
                    if naxis > 1:
                        dim_str += f'\n   [{_id}({iaxis})] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}'
                    else:
                        dim_str += f'\n   [{_id}] {_repr.make_bold(d[iaxis].name)} {d[iaxis].shape}'
                    dim_str += f'\n       long_name:     {d[iaxis].attrs.get("long_name")}'
                    dim_str += f'\n       standard_name: {d[iaxis].attrs.get("standard_name")}'
                    dim_str += f'\n       units:         {d[iaxis].attrs.get("units")}'
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

    def to_units(self, new_units: str):
        """Changes the physical unit of the dataset using pint_xarray.
        Loads to full dataset into RAM!"""
        self[()] = self[()].pint.quantify().pint.to(new_units).pint.dequantify()

    def rename(self, newname):
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
        Make sure you have write intent on file"""
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
        logger.debug(f'new primary scale: {self.dims[axis][0]}')
