"""dataset decoders"""
import h5py
import numpy as np
import xarray as xr

from .. import conventions, consts
from .. import get_config, get_ureg


def dataset_value_decoder(func):
    """decorator during slicing of dataset"""

    def wrapper(*args, **kwargs):
        """wrapper that decodes the xarray.DataArray

        Note, if offset is used, this is the formular:
        xarr = (xarr - offset) * scale
        """
        ds = args[0]
        assert isinstance(ds, h5py.Dataset)
        xarr = func(*args, **kwargs)

        parent_slice = args[1]

        if not isinstance(xarr, xr.DataArray):
            return xarr

        anc_ds = ds.ancillary_datasets
        if anc_ds:
            for name, ads in anc_ds.items():
                ads_data = ads[parent_slice]
                # if ads_data.coords != xarr.coords:
                #     raise ValueError(f'Coordinates of ancillary dataset "{name}" do not match '
                #                         f'coordinates of dataset "{ds.name}"')
                xarr = xarr.assign_coords({name: ads[parent_slice]})
            xarr.attrs[consts.ANCILLARY_DATASET] = [name for name in anc_ds.keys()]
            # print(xarr.attrs.pop(consts.ANCILLARY_DATASET))

        if xarr.dtype.type is np.str_:
            return xarr

        if not conventions.get_current_convention().use_scale_and_offset:
            return xarr
            # return H5DataArray(xarr, h5parent=ds, associated_dara_arrays=None)

        scale = xarr.attrs.pop(conventions.get_current_convention().scale_attribute_name, None)
        offset = xarr.attrs.pop(conventions.get_current_convention().offset_attribute_name, None)

        if scale and offset:
            with xr.set_options(keep_attrs=True):
                return ((xarr - offset).pint.quantify(unit_registry=get_ureg()) * scale).pint.dequantify(
                    format=get_config()['ureg_format'])

        elif scale:
            with xr.set_options(keep_attrs=True):
                return (xarr.pint.quantify(unit_registry=get_ureg()) * scale).pint.dequantify(
                    format=get_config()['ureg_format'])
        elif offset:
            with xr.set_options(keep_attrs=True):
                return xarr - offset

        if get_config('add_source_info_to_xr'):
            xarr.attrs['__hdf_src_info__'] = {'filename': str(ds.hdf_filename),
                                              'name': ds.name}
        return xarr
        # return H5DataArray(xarr, h5parent=ds, h5slice=parent_slice)

    return wrapper
