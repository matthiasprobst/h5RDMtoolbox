"""Extension to compute normalized xarray datasets and arrays"""
import pint
# import pint_xarray  # noqa: F401
import xarray as xr


def to_base_units(da: xr.DataArray) -> xr.DataArray:
    """Turns the units of an xarray to the base units, e.g. m/mm turns to dimensionless
    because pint_xarray has no method `to_base_units()`.
    """
    final_units = pint.Quantity(da.attrs['units']).to_base_units()
    return da.pint.quantify().pint.to(final_units.units).pint.dequantify()


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
        if len(coords):
            new_obj = self._obj.normalize.coords(**coords)
        else:
            new_obj = self._obj

        if 'units' not in self._obj.attrs:
            self._obj.attrs['units'] = ''

        if isinstance(data_normalization, str):
            magnitude, units = data_normalization.split(' ')
            if '.' in magnitude or 'e' in magnitude:
                data_normalization = xr.DataArray(float(data_normalization), attrs={'units': units})
            else:
                data_normalization = xr.DataArray(int(data_normalization), attrs={'units': units})
        elif isinstance(data_normalization, (int, float)):
            data_normalization = xr.DataArray(data_normalization, attrs={'units': self._obj.attrs['units']})

        if self._obj.attrs['units'] not in ('', ' ', 'dimensionless'):
            return (new_obj.pint.quantify() / data_normalization.pint.quantify().pint.to(
                self._obj.attrs['units'])).pint.dequantify()
        else:
            return (new_obj.pint.quantify() / data_normalization.pint.quantify()).pint.dequantify()

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

        if len(value) == 0:
            if len(coords) not in (1, len(self._obj.coords)):
                raise ValueError(f'Either all coordinates must be specified or only one coordinate: {len(coords)}!= (1,'
                                 f' {len(self._obj.coords)}).')

        if not isinstance(coords, dict):
            raise TypeError(f'coords must be a dictionary, not {type(coords)}.')

        for k in self._obj.coords.keys():
            if 'units' not in self._obj.coords[k].attrs:
                self._obj.coords[k].attrs['units'] = ''

        obj_coords = {k: xr.DataArray(v.values, dims=v.dims, attrs=v.attrs) for k, v in self._obj.coords.items()}

        if len(coords) == 1:
            # either the key is different to the coords, then this is used to normalize all coordinates
            # or the key is the same as the coords, then this is used to normalize only this coordinate
            coord_key = list(coords.keys())[0]
            coord_value = coords[coord_key]

            if isinstance(coord_value, (int, float)):
                coords = {coord_key: xr.DataArray(coord_value, attrs={'units': ''}) for k in obj_coords.keys()}
            elif isinstance(coord_value, str):
                quantity = pint.Quantity(coord_value)
                magnitude, units = quantity.magnitude, quantity.units
                if '.' in magnitude or 'e' in magnitude:
                    coords = {coord_key: xr.DataArray(float(magnitude), attrs={'units': units}) for k in
                              obj_coords.keys()}
                else:
                    coords = {coord_key: xr.DataArray(int(magnitude), attrs={'units': units}) for k in
                              obj_coords.keys()}
            elif isinstance(coord_value, xr.DataArray):
                coords = {coord_key: coord_value for k in obj_coords.keys()}
            else:
                raise TypeError(f'Coordinate "{coord_key}" is of type {type(coord_value)}. '
                                f'It must be either a float or an xarray data array.')

            if coord_key not in obj_coords.keys():
                updated_coords = {k: (v.pint.quantify() / coords[coord_key].pint.quantify()).pint.dequantify() for k, v
                                  in obj_coords.items()}

                ret_obj = self._obj.assign_coords(**updated_coords)
                for k in ret_obj.coords.keys():
                    ret_obj = ret_obj.rename({k: f'{k} / {coord_key}'})
                return ret_obj
            else:
                # update only specific one:
                new_coord = to_base_units((obj_coords[coord_key].pint.quantify() / coords[
                    coord_key].pint.quantify()).pint.dequantify())
                return self._obj.assign_coords(**{coord_key: new_coord})

        if not all(k in obj_coords.keys() for k in coords.keys()):
            raise ValueError('All normalization items must be coordinates if more than one item is provided.')

        ret_obj = self._obj
        for k, v in coords.items():
            ret_obj = ret_obj.normalize.coords(**{k: v})
        return ret_obj
