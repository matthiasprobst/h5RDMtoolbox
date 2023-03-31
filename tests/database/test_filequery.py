import numpy as np
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import Files
from h5rdmtoolbox.wrapper.tbx import File


class TestFileQuery(unittest.TestCase):

    def test_H5Files(self):
        h5tbx.use('tbx')
        fnames = []
        with File() as h51:
            h51.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

            with File() as h52:
                h52.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 2')
                fnames.append(h52.filename)

                with Files(fnames) as h5s:
                    self.assertTrue(len(h5s._list_of_filenames) == 2)
                    with self.assertRaises(TypeError):
                        h5s.find(2)
                    res = h5s.find({'$basename': 'ds'})
                    self.assertEqual([h51.ds, h52.ds], res)
                    res = h5s.find({'$basename': 'none'})
                    self.assertEqual(res, [])
                    # self.assertEqual(res[0].long_name[-1], '1')
                    # self.assertEqual(res[1].long_name[-1], '2')
                    res = h5s.find_one({'$basename': 'ds'})
                    self.assertEqual(h51.ds, res)

                with self.assertRaises(ValueError):
                    with Files(fnames[0]):
                        pass

                with Files(pathlib.Path(fnames[0]).parent) as h5s:
                    self.assertEqual(h5s._list_of_filenames, list(pathlib.Path(fnames[0]).parent.glob('*.hdf')))

    def test_and_find(self):
        h5tbx.use('tbx')
        with h5tbx.File() as h5:
            h5.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 1')
            h5.create_dataset('ds2', shape=(1, 2, 3), units='', long_name='long name 1')
            h5.create_dataset('ds3', shape=(1, 2, 3), units='', long_name='long name 2')
            h5.create_group('grps', long_name='long name 1')
            res = h5.find({'$basename': 'ds', 'long_name': 'long name 1'})
            self.assertEqual(res[0], h5['ds'])
            res = sorted(h5.find({'$shape': (1,2,3), 'long_name': 'long name 1'}, '$dataset'))
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0], h5['ds'])
            self.assertEqual(res[1], h5['ds2'])
            res = h5.find_one({'$shape': (1,2,3), 'long_name': 'long name 1'}, '$dataset')
            self.assertIn(res, [h5['ds'], h5['ds2']])

    def test_recursive_find(self):
        h5tbx.use(None)
        with h5tbx.File() as h5:
            gd = h5.create_group('trn_datacubes')
            gd.create_dataset('u', data=np.random.random((3, 5, 10, 20)))
            g = h5.create_group('monitors')
            g.create_dataset('pressure1', data=[1, 2, 3], attrs={'long_name': 'Pressure'})
            g.create_dataset('pressure2', data=[1, 2, 3], attrs={'long_name': 'Pressure'})

            self.assertEqual(gd.find({'long_name': 'Pressure'}, rec=True), [])
            self.assertEqual(gd.find({'long_name': 'Pressure'}, rec=False), [])
            self.assertEqual(gd.find({'$shape': (3, 5, 10, 20)}, rec=True), [gd.u])
            with self.assertRaises(AttributeError):
                gd.find({'$fail': (3, 5, 10, 20)}, objfilter='$Dataset', rec=True)

    def test_distinct(self):
        h5tbx.use(None)
        with h5tbx.File() as h5:
            gd = h5.create_group('trn_datacubes')
            gd.create_dataset('u', data=np.random.random((3, 5, 10, 20)))
            g = h5.create_group('monitors')
            g.create_dataset('pressure1', data=[1, 2, 3], attrs={'long_name': 'Pressure'})
            g.create_dataset('pressure2', data=[1, 2, 3], attrs={'long_name': 'Pressure'})

            self.assertEqual(h5.distinct('long_name', '$Dataset'), ['Pressure', ])

    def test_getitem(self):
        fnames = []
        with File() as h51:
            h51.create_dataset('ds', data=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

        with File() as h52:
            h52.create_dataset('ds', data=(4, 5, 6), units='', long_name='long name 2')
            fnames.append(h52.filename)
