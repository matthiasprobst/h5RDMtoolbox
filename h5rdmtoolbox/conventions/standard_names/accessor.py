from collections import OrderedDict

import xarray as xr
from xarray.core.rolling import DataArrayRolling

STANDARD_NAME_TRANSFORMATION_ATTR = 'STANDARD_NAME_TRANSFORMATION'

class SNTArrayRolling(DataArrayRolling):

    def mean(self, keep_attrs=True, **kwargs):
        new_obj = super().mean(keep_attrs=keep_attrs, **kwargs)
        new_obj.attrs['standard_name'] = f'rolling_mean_of_{new_obj.attrs["standard_name"]}'
        sm = OrderedDict(new_obj.attrs.get(STANDARD_NAME_TRANSFORMATION_ATTR, {}))
        sm['rolling_mean'] = {'dim': self.dim, 'window': self.window,
                              'center': self.center}
        sm.move_to_end('rolling_mean', False)
        new_obj.attrs[STANDARD_NAME_TRANSFORMATION_ATTR] = sm
        return new_obj

    def max(self):
        new_obj = super().max()
        new_obj.attrs['standard_name'] = f'maximum_of_{new_obj.attrs["standard_name"]}'
        return new_obj


class PropertyDict:

    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)


@xr.register_dataarray_accessor("snt")
class StandardNameTableAccessor:
    def __init__(self, da):
        self._da = da

    def max(self):
        new_obj = self._da.max(keep_attrs=True)
        new_obj.attrs['standard_name'] = f'maximum_of_{new_obj.attrs["standard_name"]}'
        return new_obj

    def mean(self):
        with xr.set_options(keep_attrs=True):
            new_obj = self._da.mean()
        new_obj.attrs['standard_name'] = f'arithmetic_mean_of_{new_obj.attrs["standard_name"]}'
        coord_data = self._da.coords[self._da.dims[0]]
        sm = OrderedDict(new_obj.attrs.get(STANDARD_NAME_TRANSFORMATION_ATTR, {}))
        sm['arithmetic_mean_of'] = [coord_data[0].to_dict(), coord_data[-1].to_dict()]
        sm.move_to_end('arithmetic_mean_of', False)
        new_obj.attrs[STANDARD_NAME_TRANSFORMATION_ATTR] = sm
        return new_obj

    def rolling(self, *args, **kwargs):
        return SNTArrayRolling(self._da, *args, **kwargs)

    @property
    def method(self):
        STANDARD_NAME_TRANSFORMATION = self._da.attrs.get(STANDARD_NAME_TRANSFORMATION_ATTR, None)
        if not STANDARD_NAME_TRANSFORMATION:
            return None
        return PropertyDict({k: [xr.DataArray.from_dict(vv) for vv in v] for k, v in STANDARD_NAME_TRANSFORMATION.items()})
