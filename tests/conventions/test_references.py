"""Testing the standard attributes"""
import pathlib
import unittest

from h5rdmtoolbox.convention import references
import sys
__this_dir__ = pathlib.Path(__file__).parent

TESTING_VERSIONS = (13,)


def get_python_version():
    """Get the current Python version as a tuple."""
    return sys.version_info.major, sys.version_info.minor, sys.version_info.micro


bibtext = """@ONLINE{hdf5group,
    author = {{The HDF Group}},
    title = "{Hierarchical Data Format, version 5}",
    year = {1997-NNNN},
    note = {https://www.hdfgroup.org/HDF5/},
    addendum = "(accessed: 25.09.2023)",
}"""


class TestReferences(unittest.TestCase):


    @unittest.skipUnless(get_python_version()[1] in TESTING_VERSIONS,
                         reason=f"Nur auf Python {TESTING_VERSIONS} testen")
    def test_url(self):
        self.assertFalse(references.validate_url(123))
        