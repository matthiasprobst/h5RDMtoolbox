"""dataset decoders"""
import xarray as xr

from .. import conventions

USE_OFFSET_AND_SCALE = True


def dataset_value_decoder(func):
    """decorator during slicing of dataset"""

    def wrapper(*args, **kwargs):
        """wrapper that decodes the xarray.DataArray"""
        xarr = func(*args, **kwargs)

        if not conventions.current_convention.use_scale_and_offset:
            return xarr

        scale = xarr.attrs.get(conventions.current_convention.scale_attribute_name, None)
        offset = xarr.attrs.get(conventions.current_convention.offset_attribute_name, None)

        xarr.attrs.pop('scale')
        xarr.attrs.pop('offset')

        if scale and offset:
            with xr.set_options(keep_attrs=True):
                return ((xarr + offset).pint.quantify() * scale).pint.dequantify()
        elif scale:
            with xr.set_options(keep_attrs=True):
                return (xarr.pint.quantify() * scale).pint.dequantify()
        elif offset:
            with xr.set_options(keep_attrs=True):
                return xarr + offset
        return xarr

    return wrapper
