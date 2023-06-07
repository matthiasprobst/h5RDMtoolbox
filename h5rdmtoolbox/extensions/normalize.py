"""Extension to compute normalized xarray datasets and arrays"""
# import pint_xarray  # noqa: F401
import xarray as xr


@xr.register_dataarray_accessor("normalize")
class NormalizeAccessor:
    """Accessor to normalize a data array.
    This is helpful if data is to be plotting in dimensionless coordinates.
    """

    def __init__(self, xarray_obj):
        """Initialize the accessor"""
        self._obj = xarray_obj

    def __call__(self, data_normalization, **coords):
        """normalizes the data, not the coords unless the coords are specified"""

    def coords(self, *value, **coords):
        """Normalize data

        Parameters
        ----------
        value: int, float
            Value to be used for normalization of all coordinates.
        coords: dict
            Dictionary of coordinates to be normalized. The keys are the names of the coordinates
            and the values are the values to be used for normalization. The values can either
            be floats or xarray data arrays.
        """
        if len(value) > 0 and len(coords) > 0:
            raise ValueError('Either value or coords must be specified, not both.')
        elif len(value) > 1:
            raise ValueError('Only one value can be specified.')
        elif len(value) == 1:
            coords = {k: value[0] for k in self._obj.coords.keys()}
        for k in coords:
            if k not in self._obj.coords:
                raise KeyError(f'Coordinate "{k}" is not in the dataset.')

        for k in self._obj.coords.keys():
            if 'units' not in self._obj.coords[k].attrs:
                self._obj.coords[k].attrs['units'] = ''

        new_coords = {}
        for k in coords:
            if isinstance(coords[k], (float, int)):
                new_coords[k] = xr.DataArray(coords[k], attrs={'units': self._obj.coords[k].attrs['units']})
            elif isinstance(coords[k], xr.DataArray):
                new_coords[k] = coords[k]
            else:
                raise TypeError(f'Coordinate "{k}" is of type {type(coords[k])}. '
                                f'It must be either a float or an xarray data array.')

        # hack as coordinates cannot be "pinted" (https://docs.xarray.dev/en/stable/generated/xarray.DataArray.expand_dims.html):
        old_coords = {k: xr.DataArray(v.values, attrs=v.attrs.items(), dims=v.dims) for k, v in
                      self._obj.coords.items()}

        new_coords = {k: (old_coords[k].pint.quantify() / v.pint.quantify().pint.to(
            self._obj.coords[k].attrs['units'])).pint.dequantify() for k, v in
                      new_coords.items()}

        # for k in new_coords.keys():
        #     new_coords[k].dims = self._obj.coords[k].dims
        ret_obj = self._obj.assign_coords(**new_coords)
        return ret_obj
