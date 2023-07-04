"""dataset decoders"""
import h5py
import numpy as np
import pathlib
import xarray as xr

from .. import conventions

USE_OFFSET_AND_SCALE = True


class H5DataArray(xr.DataArray):
    """Wrapper around xarray.DataArray to provide additional
    information about source (HDF5 dataset and slice)"""

    __slots__ = ('h5parent', 'h5slice')

    def __init__(self, *args, **kwargs):
        h5parent = kwargs.pop('h5parent', None)
        h5slice = kwargs.pop('h5slice', None)
        super().__init__(*args, **kwargs)
        self.h5parent = h5parent
        self.h5slice = h5slice

    @property
    def h5filename(self) -> pathlib.Path:
        """The HDF5 filename from where data was taken"""
        return self.h5parent.hdf_filename

    def __getitem__(self, key) -> "H5DataArray":
        ret = super().__getitem__(key)
        return H5DataArray(ret,
                           h5parent=self.h5parent,
                           h5slice=key)


def dataset_value_decoder(func):
    """decorator during slicing of dataset"""

    def wrapper(*args, **kwargs):
        """wrapper that decodes the xarray.DataArray"""
        ds = args[0]
        assert isinstance(ds, h5py.Dataset)
        xarr = func(*args, **kwargs)

        parent_slice = args[1]
        if not isinstance(xarr, xr.DataArray):
            return xarr

        if xarr.dtype.type is np.str_:
            return xarr

        if not conventions.current_convention.use_scale_and_offset:
            return xarr

        scale = xarr.attrs.pop(conventions.current_convention.scale_attribute_name, None)
        offset = xarr.attrs.pop(conventions.current_convention.offset_attribute_name, None)

        if scale and offset:
            with xr.set_options(keep_attrs=True):
                # note, that xarr has already the correctly (scaled) units!
                return (xarr + offset) * scale.magnitude
        elif scale:
            with xr.set_options(keep_attrs=True):
                return xarr * scale.magnitude
        elif offset:
            with xr.set_options(keep_attrs=True):
                return xarr + offset

        # if ds.has_flag_data:
        #     return FlagDataArray(xarr,
        #                          filename=ds.file.filename,
        #                          parent_slice=parent_slice)
        return H5DataArray(xarr, h5parent=ds, h5slice=parent_slice)

    return wrapper
