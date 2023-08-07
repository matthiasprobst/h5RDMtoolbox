import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx


class TestXr2HDF(unittest.TestCase):

    def test_xr2hdf(self):
        h5tbx.use(None)
        da = xr.DataArray([1, 2, 3], dims='x')
        self.assertIsInstance(da.hdf, h5tbx.wrapper.core.xr2hdf.HDFArrayAccessor)
        self.assertIsInstance(da.hdf._obj, xr.DataArray)

        with self.assertRaises(AttributeError):
            with h5tbx.File() as h5:
                da.hdf.to_group(h5, name=None)

        da.name = 'test'

        with h5tbx.File() as h5:
            da.hdf.to_group(h5, name=None)
            self.assertTrue('test' in h5)
        with h5tbx.File() as h5:
            da.hdf.to_group(h5, name='my_var')
            self.assertTrue('my_var' in h5)
            da.hdf.to_group(h5, name='my_var', overwrite=True)
            self.assertTrue('my_var' in h5)
            with self.assertRaises(ValueError):
                da.hdf.to_group(h5, name='my_var', overwrite=False)

        dax = da.assign_coords({'x': [1, 2, 3]})

        with h5tbx.File() as h5:
            dax.hdf.to_group(h5, name=None)
            self.assertTrue('test' in h5)
            self.assertTrue('x' in h5)

            dax.hdf.to_group(h5, name=None, overwrite=True)
            self.assertTrue('test' in h5)
            self.assertTrue('x' in h5)
