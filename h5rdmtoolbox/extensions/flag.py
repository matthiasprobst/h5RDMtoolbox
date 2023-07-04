"""Extension to compute magnitude of xarray datasets"""

import numpy as np
import xarray as xr

from ..wrapper.core import FLAG_DATASET_CONST, File
from ..wrapper.ds_decoder import FlagDataArray


@xr.register_dataarray_accessor("flag")
class FlagAccessor:
    """Accessor to handle flag data"""
    __slots__ = ('_obj',)

    def __init__(self, xarray_obj: FlagDataArray):
        """Initialize the accessor"""
        if not isinstance(xarray_obj, FlagDataArray):
            raise TypeError("The accessor only works with 'FlagDataArray' object, which "
                            "is a subclass of xr.DataArray and is returned if the original data "
                            "is associated with a flag dataset.")
        self._obj = xarray_obj

    def where(self, *flags, fill=None):
        if fill is None:
            fill = np.nan
        data = self.values()
        ret = data & flags[0]
        if len(flags) > 1:
            for flag in flags[1:]:
                ret |= data & flag
        masked = self._obj.where(ret, other=fill)
        return masked

    def values(self):
        # TODo think about caching if once loaded
        with File(self._obj._filename, 'r') as h5:
            return h5[self._obj._dataset_name].__getitem__(self._obj._parent_slice)

    @property
    def has_flag_data(self):
        """return True if flag data is associated with the data array"""
        return FLAG_DATASET_CONST in self._obj.attrs
    #
    # def where(self, *flags):
    #     pass
    #
    # def __call__(self, *flags):
    #     if self.has_flag_data:
    #         print(flags)
