import xarray as xr
from typing import Dict
from xarray.core.rolling import DataArrayRolling

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.protected_attributes import PROVENANCE

STANDARD_NAME_TRANSFORMATION_ATTR = 'STANDARD_NAME_TRANSFORMATION'


class SNTArrayRolling(DataArrayRolling):
    """subclass of xarray.core.rolling.DataArrayRolling that adds provenance information"""

    def _add_processing_history(self, obj, proc_hist: Dict):
        """helper function that updates the attributes with important provenance information"""
        prov = obj.attrs.get(PROVENANCE, {}).copy()
        pchist = prov.get('processing_history', None)
        if pchist is None:
            pchist = []

        pchist.append(proc_hist)
        prov['processing_history'] = pchist
        obj.attrs[PROVENANCE] = prov
        return obj

    def mean(self, keep_attrs=True, **kwargs):
        parent_info = describe_xarray(self.obj)

        new_obj = super().mean(keep_attrs=keep_attrs, **kwargs)
        new_obj.attrs['standard_name'] = f'rolling_mean_of_{new_obj.attrs["standard_name"]}'

        this_pc = {'parent': parent_info,
                   'name': 'rolling_mean_of',
                   'window': self.window,
                   'center': self.center}

        return self._add_processing_history(new_obj, this_pc)

    def std(self, keep_attrs=True, **kwargs):
        parent_info = describe_xarray(self.obj)

        new_obj = super().mean(keep_attrs=keep_attrs, **kwargs)
        new_obj.attrs['standard_name'] = f'rolling_standard_deviation_of_{new_obj.attrs["standard_name"]}'

        this_pc = {'parent': parent_info,
                   'name': 'rolling_std_of',
                   'window': self.window,
                   'center': self.center}

        return self._add_processing_history(new_obj, this_pc)

    def max(self):
        parent_info = describe_xarray(self.obj)

        new_obj = super().max()
        new_obj.attrs['standard_name'] = f'rolling_maximum_of_{new_obj.attrs["standard_name"]}'

        this_pc = {'parent': parent_info,
                   'name': 'rolling_max_of',
                   'window': self.window,
                   'center': self.center}
        return self._add_processing_history(new_obj, this_pc)


# class PropertyDict:
#
#     def __init__(self, d):
#         for k, v in d.items():
#             setattr(self, k, v)


class MFuncCaller:

    def __init__(self, da, snt, mfunc):
        self._mfunc = mfunc
        self._snt = snt
        self._da = da

    def __call__(self, **kwargs):
        return self._mfunc(self._da, self._snt, **kwargs)


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


@xr.register_dataarray_accessor("snt")
class StandardNameTableAccessor:
    def __init__(self, da):
        self._da = da

        # get snt:
        self._snt = None

        filename = da.attrs.get('PROVENANCE', None).get('HDF', None).get('filename', None)
        if filename:
            with h5tbx.File(filename, mode='r') as h5:
                self._snt = h5tbx.conventions.standard_names.StandardNameTable.from_zenodo(
                    h5.attrs.raw['standard_name_table'])

        if self._snt:
            for t in self._snt.transformations:
                if t.mfunc:
                    setattr(self, t.name, MFuncCaller(self._da, self._snt, t.mfunc))

    def __call__(self):
        return self._snt

    def __getitem__(self, item):
        history = self._da.attrs.get('history', [])
        history.append({'parent': describe_xarray(self._da),
                        'name': '__getitem__'})
        new_da = self._da[item]
        new_da.attrs[PROVENANCE]['processing_history'] = history
        return new_da

    def rolling(self, dim=None, min_periods=None, center: bool = False, **window_kwargs):
        """see xarray.core.dataarray.DataArray.rolling"""
        from xarray.core.utils import either_dict_or_kwargs
        dim = either_dict_or_kwargs(dim, window_kwargs, "rolling")
        return SNTArrayRolling(self._da, dim, min_periods=min_periods, center=center)
