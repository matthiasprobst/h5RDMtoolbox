"""Testing the standard attributes"""
import pathlib
import unittest

from h5rdmtoolbox.convention import references

__this_dir__ = pathlib.Path(__file__).parent

bibtext = """@ONLINE{hdf5group,
    author = {{The HDF Group}},
    title = "{Hierarchical Data Format, version 5}",
    year = {1997-NNNN},
    note = {https://www.hdfgroup.org/HDF5/},
    addendum = "(accessed: 25.09.2023)",
}"""


class TestReferences(unittest.TestCase):

    def test_url(self):
        self.assertFalse(references.validate_url(123))
        