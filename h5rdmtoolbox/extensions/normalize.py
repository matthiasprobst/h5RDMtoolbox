"""Extension to compute normalized xarray datasets and arrays"""
import pint
# import pint_xarray  # noqa: F401
import xarray as xr
from typing import Union, Dict

import h5rdmtoolbox as h5tbx


def to_base_units(da: xr.DataArray) -> xr.DataArray:
    """Turns the units of an xarray to the base units, e.g. m/mm turns to dimensionless
    because pint_xarray has no method `to_base_units()`.
    """
    final_units = pint.Quantity(da.attrs['units']).to_base_units()
    return da.pint.quantify(unit_registry=h5tbx.get_ureg()).pint.to(final_units.units).pint.dequantify()


@xr.register_dataarray_accessor("normalize")
class NormalizeAccessor:
    """Accessor to normalize a data array.
    This is helpful if data is to be plotting in dimensionless coordinates.
    """

    def __init__(self, xarray_obj):
        """Initialize the accessor"""
        self._obj = xarray_obj

    def __call__(self, rename=False, **data: Union[str, Dict]):
        """normalizes the data, not the coords unless the coords are specified"""

        norm_obj = self._obj
        for k, v in data.items():
            norm_obj = NormalizeAccessor._normalize(norm_obj, k, v, rename)

        return norm_obj

    @staticmethod
    def _normalize(obj, name, value, rename):
        if isinstance(value, str):
            qobj = obj.pint.quantify(unit_registry=h5tbx.get_ureg())
            q = h5tbx.get_ureg()(value)
            norm_obj = (qobj/q).pint.dequantify()
        elif isinstance(value, (int, float)):
            # user indicates a float or int, which is interpreted as dimensionless
            with xr.set_options(keep_attrs=True):
                norm_obj = obj / value
        else:
            raise TypeError(f'Normalization must be either a string or a float, not {type(v)}.')

        if rename:
            norm_obj.name = f'{obj.name}_{name}'
        else:
            norm_obj.name = obj.name
        comment = norm_obj.attrs.get('comment', '')
        if comment != '':
            comment += ' '
        comment += f'Normalized by {name}={value}'
        norm_obj.attrs['comment'] = comment
        return norm_obj

    def coords(self, rename: bool = False, **coords):
        """Normalize coordinate data

        Parameters
        ----------
        rename : bool, optional
            If True, the coordinate names are renamed to the normalized names, by default False
        coords : Dict[str, Union[str, int, float]]
            The coordinates to normalize. The key is the either a dictionary of key-value paris
            where the value is a string or a float. In this case the value is interpreted as the
            normalization quantity. Alternatively, the value of the key-value pair can be a dictionary
            itself, then the key is interpreted as the name of the normalized coordinate and the value
            is interpreted as the normalization quantity.
        """
        if all(isinstance(v, dict) for v in coords.values()):
            # normalize only specific coordinates
            ret_obj = self._obj
            for coord_name, norm_data in coords.items():
                norm_coord = ret_obj[coord_name].normalize(rename, **norm_data)
                ret_obj = ret_obj.assign_coords({coord_name: norm_coord})
            return ret_obj

        _update_coords = {}
        for coord_name in self._obj.coords:
            obj_norm = self._obj[coord_name]
            for k, v in coords.items():
                obj_norm = NormalizeAccessor._normalize(xr.DataArray(obj_norm), k, v, rename)
            _update_coords[coord_name] = obj_norm
        ret_obj = self._obj.assign_coords(**_update_coords)
        if rename:
            for k, v in _update_coords.items():
                ret_obj = ret_obj.rename({k: v.name})
        return ret_obj
