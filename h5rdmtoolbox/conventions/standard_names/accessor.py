from collections import OrderedDict

import xarray as xr
from xarray.core.rolling import DataArrayRolling

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.protected_attributes import PROVENANCE

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

    def max(self):
        new_obj = self._da.max(keep_attrs=True)
        new_obj.attrs['standard_name'] = f'maximum_of_{new_obj.attrs["standard_name"]}'
        return new_obj

    # def mean(self):
    #     with xr.set_options(keep_attrs=True):
    #         new_obj = self._da.mean()
    #     new_obj.attrs['standard_name'] = f'arithmetic_mean_of_{new_obj.attrs["standard_name"]}'
    #     coord_data = self._da.coords[self._da.dims[0]]
    #     sm = OrderedDict(new_obj.attrs.get(STANDARD_NAME_TRANSFORMATION_ATTR, {}))
    #     sm['arithmetic_mean_of'] = [coord_data[0].to_dict(), coord_data[-1].to_dict()]
    #     sm.move_to_end('arithmetic_mean_of', False)
    #     new_obj.attrs[STANDARD_NAME_TRANSFORMATION_ATTR] = sm
    #     return new_obj

    def rolling(self, *args, **kwargs):
        return SNTArrayRolling(self._da, *args, **kwargs)

    @property
    def method(self):
        STANDARD_NAME_TRANSFORMATION = self._da.attrs.get(STANDARD_NAME_TRANSFORMATION_ATTR, None)
        if not STANDARD_NAME_TRANSFORMATION:
            return None
        return PropertyDict(
            {k: [xr.DataArray.from_dict(vv) for vv in v] for k, v in STANDARD_NAME_TRANSFORMATION.items()})

    def get_provenance(self):
        return self._da.attrs.get(PROVENANCE, None)
        prov = self._da.attrs.get(PROVENANCE, None)
        if prov:
            for k, v in prov.get('SNT', {}).items():
                print(k, v)
                coord_from = xr.DataArray.from_dict(v['arithmetic_mean_of'][0])
                coord_to = xr.DataArray.from_dict(v['arithmetic_mean_of'][1])
        return coord_from, coord_to
