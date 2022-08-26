import unittest

from h5rdmtoolbox import tutorial
from h5rdmtoolbox.x2hdf.cfd import cfx2hdf


class TestCFD2HDF(unittest.TestCase):

    def test_AnsysCFX2HDF(self):
        hdf_filename = cfx2hdf(tutorial.CFX.get_cfx_filename())
        self.assertTrue(hdf_filename.exists())
