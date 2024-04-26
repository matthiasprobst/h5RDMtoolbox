import unittest

import h5rdmtoolbox as h5tbx


class TestLazy(unittest.TestCase):

    def test_lazyObject(self):
        with h5tbx.File() as h5:
            h5.attrs['name'] = 'test'
            lobj = h5tbx.wrapper.lazy.LHDFObject(h5)
            self.assertEqual(lobj.name, '/')
        self.assertEqual(lobj.name, '/')
        self.assertEqual(lobj.filename, h5.hdf_filename)
        self.assertEqual(lobj.attrs['name'], 'test')
