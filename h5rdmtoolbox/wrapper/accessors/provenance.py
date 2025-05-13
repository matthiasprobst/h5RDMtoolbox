import xarray as xr

try:
    from xarray.core.rolling import DataArrayRolling
except ImportError:
    # for xarray >= 2025.3.0:
    from xarray.computation.rolling import DataArrayRolling

from h5rdmtoolbox.protected_attributes import PROVENANCE


def describe_xarray(da: xr.DataArray):
    """return dictionary with dim, coord and attrs of an xarray data array"""
    if not isinstance(da, xr.DataArray):
        raise NotImplementedError(f'Only implemented for xarray.DataArray but got {type(da)}')
    dims_shape = {d: len(da[d]) for d in da.dims}
    coord_bounds = {c: [da[c][0].to_dict(), da[c][-1].to_dict()] for c in da.coords}
    attrs = da.attrs.copy()
    attrs.pop('PROVENANCE')
    if 'units' in attrs:
        attrs['units'] = str(attrs['units'])
    return dict(dims_shape=dims_shape, coord_bounds=coord_bounds, attrs=attrs)


@xr.register_dataarray_accessor("prov")
class ProvenanceAccessor:
    def __init__(self, da):
        self._da = da

    def __getitem__(self, item):
        history = self._da.attrs.get('history', [])
        history.append({'parent': describe_xarray(self._da),
                        'name': '__getitem__'})
        new_da = self._da[item]
        new_da.attrs[PROVENANCE]['processing_history'] = history
        return new_da
