"""dataset decoders"""
import numpy as np
import xarray as xr

from .. import conventions

USE_OFFSET_AND_SCALE = True


def dataset_value_decoder(func):
    """decorator during slicing of dataset"""

    def wrapper(*args, **kwargs):
        """wrapper that decodes the xarray.DataArray"""
        xarr = func(*args, **kwargs)

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
        return xarr

    return wrapper
