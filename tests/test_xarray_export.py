import json
import pathlib
import unittest

import xarray as xr

import h5rdmtoolbox as h5tbx
from datetime import datetime
logger = h5tbx.logger
# logger.setLevel('ERROR')
__this_dir__ = pathlib.Path(__file__).parent


class TestXrExport(unittest.TestCase):

    def test_export_1Dda(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset('ds', data=3, dtype='int64')
            da = ds[()]

        self.assertIsInstance(da, xr.DataArray)
        nc_fname = h5tbx.utils.generate_temporary_filename(suffix='.nc')
        da.to_netcdf(nc_fname)
        da2 = xr.open_dataarray(nc_fname)
        self.assertIsInstance(da2, xr.DataArray)
        self.assertEqual(da2[()], da[()])

    def test_export_timedata(self):
        with h5tbx.File() as h5:
            ds = h5.create_time_dataset('ds', data=datetime.now(),
                                        time_format='iso')
            da = ds[()]

        self.assertIsInstance(da, xr.DataArray)
        nc_fname = h5tbx.utils.generate_temporary_filename(suffix='.nc')

        for ak in da.attrs.keys():
            if isinstance(da.attrs[ak], dict):
                da.attrs[ak] = json.dumps(da.attrs[ak])

        da.to_netcdf(nc_fname)
        da2 = xr.open_dataarray(nc_fname)
        self.assertIsInstance(da2, xr.DataArray)
        self.assertEqual(da2[()], da[()])
