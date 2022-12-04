import pathlib
import unittest

from h5rdmtoolbox.database import Files
from h5rdmtoolbox.wrapper.cflike import H5File


class TestFileQuery(unittest.TestCase):

    def test_H5Files(self):
        fnames = []
        with H5File() as h51:
            h51.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

            with H5File() as h52:
                h52.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 2')
                fnames.append(h52.filename)

                with Files(fnames) as h5s:
                    self.assertTrue(len(h5s._list_of_filenames) == 2)
                    res = h5s.find({'$basename': 'ds'})
                    self.assertEqual([h51.ds, h52.ds], res)
                    # self.assertEqual(res[0].long_name[-1], '1')
                    # self.assertEqual(res[1].long_name[-1], '2')
                    res = h5s.find_one({'$basename': 'ds'})
                    self.assertEqual(h51.ds, res)

                with self.assertRaises(ValueError):
                    with Files(fnames[0]):
                        pass

                with Files(pathlib.Path(fnames[0]).parent) as h5s:
                    self.assertEqual(h5s._list_of_filenames, list(pathlib.Path(fnames[0]).parent.glob('*.hdf')))

    def test_getitem(self):
        fnames = []
        with H5File() as h51:
            h51.create_dataset('ds', data=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

        with H5File() as h52:
            h52.create_dataset('ds', data=(4, 5, 6), units='', long_name='long name 2')
            fnames.append(h52.filename)
