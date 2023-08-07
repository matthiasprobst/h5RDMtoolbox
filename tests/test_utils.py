import datetime
import pathlib
import unittest

import h5rdmtoolbox as h5tbx

__this_dir__ = pathlib.Path(__file__).parent


class TestUtils(unittest.TestCase):

    def test_touch_tmp_hdf5_file(self):
        now = datetime.datetime.now()
        tmp_hdf5file = h5tbx.utils.touch_tmp_hdf5_file(touch=True,
                                                       attrs={'dtime': now})
        self.assertTrue(h5tbx.UserDir['tmp'] in tmp_hdf5file.parents)

    def test_has_datasets(self):
        with h5tbx.use(None):
            with h5tbx.File() as h5:
                self.assertFalse(h5tbx.utils.has_datasets(h5))
                h5.create_dataset('test', data=1)
                self.assertTrue(h5tbx.utils.has_datasets(h5))
                self.assertFalse(h5tbx.utils.has_groups(h5))
                h5.create_group('testgroup')
                self.assertTrue(h5tbx.utils.has_groups(h5))

            self.assertTrue(h5tbx.utils.has_datasets(h5.hdf_filename))
            self.assertTrue(h5tbx.utils.has_groups(h5.hdf_filename))
