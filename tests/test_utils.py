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
        self.assertTrue(h5tbx.user_dirs['tmp'] in tmp_hdf5file.parents)




