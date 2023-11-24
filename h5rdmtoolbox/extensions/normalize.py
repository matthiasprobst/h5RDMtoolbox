"""Extension to compute normalized xarray datasets and arrays"""
import pint
# import pint_xarray  # noqa: F401
import xarray as xr
from typing import Union, Dict

import h5rdmtoolbox as h5tbx

NORM_DELIMITER = '/'


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

    def __call__(self, data: Dict = None, rename=False, **data_kwargs):
        """normalizes the data, not the coords unless the coords are specified.

        Parameters
        ----------
        data : Dict
            The data to normalize. The key is used to have a variable name for the normalized data.s
        rename : bool, optional
            If True, the data is renamed to the normalized name, by default False
        """
        if not isinstance(rename, bool):
            raise TypeError(f'rename must be a boolean, not {type(rename)}.')

        if data is None:
            data = {}
        data.update(data_kwargs)

        norm_obj = self._obj
        for k, v in data.items():
            norm_obj = NormalizeAccessor._normalize(norm_obj, k, v, rename)

        return norm_obj

    @staticmethod
    def _normalize(obj, name, value, rename):
        if isinstance(value, str):
            qobj = xr.DataArray(obj).pint.quantify(unit_registry=h5tbx.get_ureg())
            q = h5tbx.get_ureg().Quantity(value)
            norm_obj = (qobj / q).pint.dequantify()
        elif isinstance(value, (int, float)):
            # user indicates a float or int, which is interpreted as dimensionless
            with xr.set_options(keep_attrs=True):
                norm_obj = obj / value
        else:
            raise TypeError(f'Normalization must be either a string or a float, not {type(value)}.')

        if rename:
            norm_obj.name = f'{obj.name}{NORM_DELIMITER}{name}'
        else:
            norm_obj.name = obj.name
        comment = norm_obj.attrs.get('comment', '')
        if comment != '':
            comment += ' '
        comment += f'Normalized by {name}={value}'
        norm_obj.attrs['comment'] = comment
        return norm_obj

    def coords(self, value_or_coord_dict: Dict[str, Union[str, int, float]] = None, rename: bool = False, **coords):
        """Normalize coordinate data

        Parameters
        ----------
        value_or_coord_dict : Dict[str, Union[str, int, float]]
            The coordinates to normalize. The key is the either a dictionary of key-value paris
            where the value is a string or a float. In this case the value is interpreted as the
            normalization quantity. Alternatively, the value of the key-value pair can be a dictionary
            itself, then the key is interpreted as the name of the normalized coordinate and the value
            is interpreted as the normalization quantity.
        rename : bool, optional
            If True, the coordinate names are renamed to the normalized names, by default False

        Examples
        --------
        >>> import h5rdmtoolbox as h5tbx
        >>> with h5tbx.File() as h5:
        ...     h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
        ...     h5.create_dataset('y', data=[1, 2, 3, 4], make_scale=True)
        ...     h5.create_dataset('u', data=np.random.random((4, 3)), attach_scales=('y', 'x'))
        ...     u_xnorm = h5['u'][:].normalize.coords(L='3m', rename=True)
        >>> u_xnorm.plot.contourf()
        >>> plt.show()
        """
        if not isinstance(rename, bool):
            raise TypeError(f'rename must be a boolean, not {type(rename)}.')

        if isinstance(value_or_coord_dict, (int, float, str)):
            value_or_coord_dict = {k: value_or_coord_dict for k in self._obj.coords}

        if value_or_coord_dict is None:
            value_or_coord_dict = {}
        value_or_coord_dict.update(coords)

        def _key_is_coord_name(_key):
            return _key in self._obj.coords

        if not all(_key_is_coord_name(k) for k in value_or_coord_dict):
            # if none coord name is specified
            value_or_coord_dict = {cname: value_or_coord_dict for cname in self._obj.coords}
        else:
            for k in value_or_coord_dict:
                if k not in self._obj.coords:
                    raise KeyError(f'{k} is not an existing coordinate. These are: {self._obj.coords}')

        # _coord_dict = value_or_coord_dict.copy()
        # for k, v in value_or_coord_dict.items():
        #     if isinstance(v, (int, float, str)):
        #         _coord_dict.pop(k)
        #         for coord_name in self._obj.coords.keys():
        #             _coord_dict[coord_name] = {k: v}

        if all(isinstance(v, dict) for v in value_or_coord_dict.values()):
            # normalize only specific coordinates
            ret_obj = self._obj
            for coord_name, norm_data in value_or_coord_dict.items():
                norm_coord = ret_obj[coord_name].normalize(norm_data, rename)
                ret_obj = ret_obj.assign_coords({coord_name: norm_coord})
                if rename:
                    ret_obj = ret_obj.rename({coord_name: norm_coord.name})
            return ret_obj

        _update_coords = {}

        for coord_name, v in value_or_coord_dict.items():
            obj_norm = self._obj[coord_name]
            if isinstance(v, dict):
                for ak, av in v.items():
                    obj_norm = NormalizeAccessor._normalize(xr.DataArray(obj_norm), ak, av, rename)
            else:
                # no renaming, because
                obj_norm = NormalizeAccessor._normalize(xr.DataArray(obj_norm), coord_name, v, False)
            _update_coords[coord_name] = obj_norm

        # for coord_name in self._obj.coords:
        #     obj_norm = self._obj[coord_name]
        #     for k, v in value_or_coord_dict.items():
        #         if isinstance(v, dict):
        #             for ak, av in v.items():
        #                 obj_norm = NormalizeAccessor._normalize(xr.DataArray(obj_norm), ak, av, rename)
        #         else:
        #             obj_norm = NormalizeAccessor._normalize(xr.DataArray(obj_norm), k, v, rename)
        #     _update_coords[coord_name] = obj_norm
        ret_obj = self._obj.assign_coords(**_update_coords)
        if rename:
            for k, v in _update_coords.items():
                if k != v.name:
                    ret_obj = ret_obj.rename({k: v.name})
        return ret_obj
