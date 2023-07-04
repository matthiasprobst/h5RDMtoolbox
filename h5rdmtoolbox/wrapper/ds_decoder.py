"""dataset decoders"""
import h5py
import numpy as np
import xarray as xr

from .. import conventions

USE_OFFSET_AND_SCALE = True


class FlagDataArray(xr.DataArray):
    """Wrapper around xarray.DataArray to allow working with flag data"""
    __slots__ = ('_filename', '_parent_slice', '_dataset_name')

    def __init__(self, *args, **kwargs):
        _filename = kwargs.pop('filename', None)
        _parent_slice = kwargs.pop('parent_slice', None)
        super().__init__(*args, **kwargs)
        self._filename = _filename
        self._parent_slice = _parent_slice
        self._dataset_name = self.attrs.get('FLAG_DATASET', None)

    def __getitem__(self, key) -> "FlagDataArray":
        ret = super().__getitem__(key)
        return FlagDataArray(ret, filename=self._filename, parent_slice=key)


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

        if ds.has_flag_data:
            return FlagDataArray(xarr,
                                 filename=ds.file.filename,
                                 parent_slice=parent_slice)
        return xarr

    return wrapper
