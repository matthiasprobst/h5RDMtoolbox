"""dataset decoders"""
import h5py
import numpy as np
import xarray as xr

from .. import conventions, consts


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

        if not conventions.current_convention.use_scale_and_offset:
            return xarr
            # return H5DataArray(xarr, h5parent=ds, associated_dara_arrays=None)

        scale = xarr.attrs.pop(conventions.current_convention.scale_attribute_name, None)
        offset = xarr.attrs.pop(conventions.current_convention.offset_attribute_name, None)

        if scale and offset:
            with xr.set_options(keep_attrs=True):
                # note, that xarr has already the correctly (scaled) units!
                return (xarr + offset) * scale.magnitude
                # return H5DataArray((xarr + offset) * scale.magnitude, h5parent=ds, h5slice=parent_slice)
        elif scale:
            with xr.set_options(keep_attrs=True):
                return xarr * scale.magnitude
        elif offset:
            with xr.set_options(keep_attrs=True):
                return xarr + offset
                # return H5DataArray(xarr + offset, h5parent=ds, h5slice=parent_slice)

        # if ds.has_flag_data:
        #     return FlagDataArray(xarr,
        #                          filename=ds.file.filename,
        #                          parent_slice=parent_slice)
        return xarr
        # return H5DataArray(xarr, h5parent=ds, h5slice=parent_slice)

    return wrapper
