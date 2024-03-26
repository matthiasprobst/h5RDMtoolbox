import xarray as xr
from h5rdmtoolbox import get_ureg


@xr.register_dataarray_accessor("to")
class UnitConversionAccessor:
    """Accessor to convert units of data array. It is
    also possible to convert its coordinates"""

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def __call__(self, *args, **kwargs):
        new_obj = self._obj.copy()
        if len(args) > 0:
            for arg in args:
                if isinstance(arg, str):
                    new_obj = new_obj.pint.quantify(unit_registry=get_ureg()).pint.quantify(unit_registry=get_ureg()).pint.to(arg).pint.dequantify()
                elif isinstance(arg, dict):
                    for k, v in arg.items():
                        new_obj.coords[k] = self._obj.coords[k].pint.quantify(unit_registry=get_ureg()).pint.to(v).pint.dequantify()
        for k, v in kwargs.items():
            new_obj.coords[k] = self._obj.coords[k].pint.quantify(unit_registry=get_ureg()).pint.to(v).pint.dequantify()
        return new_obj
