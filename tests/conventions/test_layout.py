import pathlib
import unittest

from psutil._compat import FileExistsError

from h5rdmtoolbox.conventions.layout import H5Layout
from h5rdmtoolbox import H5File


class TestCnventions(unittest.TestCase):

    def setUp(self) -> None:
        """before tests"""
        self.filenames = []

    def tearDown(self) -> None:
        """cleanup if neeede"""
        for fname in self.filenames:
            f = pathlib.Path(fname)
            if f.exists():
                f.unlink()

    def test_registering(self):
        with H5File() as h5:
            h5.attrs['hello'] = 'world'
        self.filenames.append(h5.hdf_filename)

        layout = H5Layout(h5.hdf_filename)
        registered_filename = layout.register()
        self.filenames.append(registered_filename)

        self.assertTrue(registered_filename.exists())
        registered_filename.unlink()

        registered_filename = layout.register(name='test.hdf')
        self.filenames.append(registered_filename)

        self.assertTrue(registered_filename.exists())
        with self.assertRaises(FileExistsError):
            layout.register(name='test.hdf')

        registered_filename = layout.register(name='test.hdf', overwrite=True)
        self.filenames.append(registered_filename)
        registered_filename.unlink()

        layout = H5Layout(h5.hdf_filename)
        registered_filename = layout.register(name='mylayout.hdf')
        self.filenames.append(registered_filename)

        h5lay = H5Layout.load_registered('mylayout.hdf')
        self.assertTrue(h5lay.filename.exists())

        h5lay = H5Layout.load_registered('mylayout')
        self.assertTrue(h5lay.filename.exists())

        with self.assertRaises(FileNotFoundError):
            H5Layout.load_registered('helloworld')
