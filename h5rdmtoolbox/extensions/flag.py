"""Extension to compute magnitude of xarray datasets"""

import numpy as np
import xarray as xr

from ..wrapper.core import FLAG_DATASET_CONST, File
from ..wrapper.ds_decoder import H5DataArray


@xr.register_dataarray_accessor("flag")
class FlagAccessor:
    """Accessor to handle flag data"""
    __slots__ = ('_obj',)

    def __init__(self, xarray_obj: H5DataArray):
        """Initialize the accessor"""
        self._obj = xarray_obj
        if 'FLAG_DATASET' not in self._obj.attrs:
            raise KeyError('Dataset is not associated with a flag dataset')

    def where(self, *flags, fill=np.NAN) -> xr.DataArray:
        """filter for flags. Returns data where the flags are set to the
        fill value (default: np.NAN)

        Parameters
        ----------
        flags : int or list of int
            flag(s) to filter for (bitwise and)
        fill : float, optional
            value to fill the data where the flags are not set, by default None,
            which means np.NAN
        """
        flag_data = self.values()
        ret = flag_data & flags[0]
        if len(flags) > 1:
            for flag in flags[1:]:
                ret |= flag_data & flag
        masked = self._obj.where(ret, other=fill)
        return masked

    def values(self) -> xr.DataArray:
        """Return the flag data as xarray.DataArray with same shape as source
        data"""
        if self._obj.h5parent.name is None:  # file might be closed
            with File(self._obj.h5parent.hdf_filename) as h5:
                return h5[self._obj.attrs['FLAG_DATASET']][self._obj.h5slice]
        return self._obj.h5parent.rootparent[self._obj.attrs['FLAG_DATASET']][self._obj.h5slice]

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
