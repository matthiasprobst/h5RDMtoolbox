"""dataset decoders"""
import h5py
import numpy as np
import xarray as xr

from .. import consts, get_ureg, get_config, protected_attributes


def scale_and_offset_decoder(xarr: xr.DataArray, ds: h5py.Dataset) -> xr.DataArray:
    """Assumes that scale and offset are available as attributes. The return value is a new xarray.DataArray,
    which data has been transformed according to ret = (xarr - offset) * scale
    """
    scale = xarr.attrs.pop('scale', None)
    offset = xarr.attrs.pop('offset', None)

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

    return xarr


# dataset_decoders = {'scale_and_offset': scale_and_offset_decoder}
registered_dataset_decoders = {'scale_and_offset': scale_and_offset_decoder}
decoder_names = ()


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

        if get_config('add_source_info_to_xr'):
            xarr.attrs[protected_attributes.HDF_SRC_FILENAME] = {'filename': str(ds.hdf_filename),
                                                                 'name': ds.name}

        if xarr.dtype.type is np.str_:
            return xarr

        for decoder_name in decoder_names:
            try:
                xarr = registered_dataset_decoders[decoder_name](xarr, ds)
            except Exception as e:
                raise Exception(
                    f'Error during decoding of dataset "{ds.name}" with decoder "{decoder_name}": {e}') from e
        return xarr

    return wrapper
