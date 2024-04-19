"""dataset decoders"""

import h5py
import numpy as np
import xarray as xr

from .. import consts, get_ureg, get_config, protected_attributes


def scale_and_offset_decoder(xarr: xr.DataArray, ds: h5py.Dataset) -> xr.DataArray:
    """Assumes that scale and offset are available as attributes. The return value is a new xarray.DataArray,
    which data has been transformed according to ret = xarr * scale + offset
    depending on the units of xarr and offset.
    """

    def _quantify(obj):
        return obj.pint.quantify(unit_registry=get_ureg())

    def _dequantify(obj):
        return obj.pint.dequantify(format=get_config()['ureg_format'])

    scale = xarr.attrs.pop('DATA_SCALE', None)
    offset = xarr.attrs.pop('DATA_OFFSET', None)

    if scale and offset:
        if isinstance(scale, h5py.Dataset):
            scale_xrda = scale[()]
        else:
            scale_xrda = ds.rootparent[scale][()]
        if isinstance(offset, h5py.Dataset):
            offset_xrda = offset[()]
        else:
            offset_xrda = ds.rootparent[offset][()]

        with xr.set_options(keep_attrs=True):
            return _dequantify(_quantify(xarr) * _quantify(scale_xrda) + _quantify(offset_xrda))

    elif scale:
        if isinstance(scale, h5py.Dataset):
            scale_xrda = scale[()]
        else:
            scale_xrda = ds.rootparent[scale][()]
        return _dequantify(_quantify(xarr) * _quantify(scale_xrda))

    elif offset:
        if isinstance(offset, h5py.Dataset):
            offset_xrda = offset[()]
        else:
            offset_xrda = ds.rootparent[offset][()]
        with xr.set_options(keep_attrs=True):
            return _dequantify(_quantify(xarr) + _quantify(offset_xrda))

    for a in ('IS_DATA_SCALE', 'IS_DATA_SCALE', 'DATA_SCALE' 'DATA_OFFSET'):
        xarr.attrs.pop(a, None)

    return xarr


# dataset_decoders = {'scale_and_offset': scale_and_offset_decoder}
registered_dataset_decoders = {'scale_and_offset': scale_and_offset_decoder}
decoder_names = ()


def dataset_value_decoder(func):
    """decorator during slicing of dataset"""

    def wrapper(*args, **kwargs):
        """wrapper that decodes the xarray.DataArray object"""
        ds = args[0]
        assert isinstance(ds, h5py.Dataset)
        kwargs.update(links_as_strings=True)
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

        if get_config('add_provenance'):
            prov_data = {
                'HDF': {
                    'root': dict(ds.rootparent.attrs.raw),
                    'group': dict(ds.parent.attrs.raw)
                }
            }
            prov_data['HDF']['filename'] = str(ds.hdf_filename.absolute())

            if protected_attributes.PROVENANCE not in xarr.attrs:
                xarr.attrs[protected_attributes.PROVENANCE] = prov_data

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
