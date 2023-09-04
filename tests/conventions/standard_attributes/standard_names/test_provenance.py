import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.protected_attributes import PROVENANCE


class MFuncCaller:

    def __init__(self, da, snt, mfunc):
        self._mfunc = mfunc
        self._snt = snt
        self._da = da

    def __call__(self, *args, **kwargs):
        return self._mfunc(self._da, self._snt)


@xr.register_dataarray_accessor("snt")
class StandardNameTableAccessor:

    def __init__(self, da):
        self._da = da

        # get snt:
        self._snt = None

        prov = da.attrs.get(PROVENANCE, None)
        if prov:
            try:
                filename = prov['HDF']['filename']
            except KeyError:
                filename = None
            if filename:
                with h5tbx.File(filename) as h5:
                    self._snt = h5tbx.conventions.standard_names.StandardNameTable.from_zenodo(
                        h5.attrs.raw['standard_name_table'])

        if self._snt:
            for t in self._snt.transformations:
                if t.mfunc:
                    setattr(self, t.name, MFuncCaller(self._da, self._snt, t.mfunc))

    def __call__(self):
        return self._snt

    def get_provenance(self):
        attrs = self._da.attrs
        if PROVENANCE not in attrs:
            raise KeyError(f'key "{PROVENANCE}" not in attributes.')
        coord_from = xr.DataArray.from_dict(attrs[PROVENANCE]['arithmetic_mean_of'][0])
        coord_to = xr.DataArray.from_dict(attrs[PROVENANCE]['arithmetic_mean_of'][1])
        return coord_from, coord_to


class TestProvenance(unittest.TestCase):

    def test_provenance(self):
        zenodo_cv = h5tbx.conventions.from_zenodo('https://zenodo.org/record/8301535')
        sn_cv = zenodo_cv.pop('contact', 'comment', 'references', 'data_type')
        sn_cv.name = 'standard name convention'
        sn_cv.register()

        h5tbx.use(sn_cv)

        with h5tbx.File() as h5:
            h5.create_dataset('u', data=[1, 2, 3, 4], standard_name='x_velocity', units='m/s')
            u = h5.u[:]

        u_mean = u.snt.arithmetic_mean_of()
        self.assertTrue('PROVENANCE' in u_mean.attrs)
        self.assertIn('arithmetic_mean_of', u_mean.attrs['PROVENANCE']['SNT'])

        with h5tbx.File() as h5:
            h5.create_dataset('u_mean', data=u_mean)
            um = h5['u_mean'][()]

        self.assertTrue('PROVENANCE' in um.attrs)
        self.assertIn('arithmetic_mean_of', um.attrs['PROVENANCE']['SNT'])
