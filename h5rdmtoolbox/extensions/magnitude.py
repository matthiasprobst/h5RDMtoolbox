"""Extension to compute magnitude of xarray datasets"""
import numpy as np

import xarray as xr
from typing import Union, Dict


@xr.register_dataset_accessor("magnitude")
class MagnitudeAccessor:
    """Accessor to convert units of data array. It is
    also possible to convert its coordinates"""

    def __init__(self, xarray_obj):
        """Initialize the accessor"""
        self._obj = xarray_obj

    def compute_from(self,
                     *data_vars,
                     name: Union[str, None] = None,
                     inplace: bool = True,
                     attrs: Union[Dict, None] = None,
                     overwrite: bool = False):
        """compute magnitude from data variable names
        Parameters
        ----------
        data_vars: str
            Names of data variables to compute magnitude from.
        name: str
            Name of the magnitude variable to be used in the dataset.
            If None, the name is automatically generated. Example: 'magnitude_of_u_v_w'
            if data_vars = ['u', 'v', 'w']
        inplace: bool
            If True, the magnitude variable is added to the dataset.
            Otherwise, a new dataset is returned.
        attrs: dict
            Attributes to be added to the magnitude variable
        overwrite: bool
            If True, the magnitude variable is overwritten if it already exists in the dataset.
        """
        mag2 = self._obj[data_vars[0]].pint.quantify() ** 2
        for data_var in data_vars[1:]:
            mag2 += self._obj[data_var].pint.quantify() ** 2
        with xr.set_options(keep_attrs=True):
            mag = np.sqrt(mag2).pint.dequantify()

        joined_names = '_'.join(data_vars)
        if name is None:
            name = f'magnitude_of_{joined_names}'
        if name in self._obj:
            if not overwrite:
                raise KeyError(f'The name of variable "{name}" is already exists in the dataset.')
            del self._obj[name]
        mag.name = name
        processing_comment = 'processing_comment'
        while processing_comment in mag.attrs:
            processing_comment = f'_{processing_comment}'
        mag.attrs['processing_comment'] = f'computed from: {joined_names.replace("_", ", ")}'
        if attrs:
            mag.attrs.update(attrs)
        if inplace:
            self._obj[name] = mag
            return self._obj
        return mag
