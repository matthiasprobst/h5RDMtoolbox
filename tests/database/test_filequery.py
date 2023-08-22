import numpy as np
import pandas as pd
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import Files
from h5rdmtoolbox.database.files import H5Objects, DatasetValues
from h5rdmtoolbox.wrapper.core import File


class TestFileQuery(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_regex(self):
        from h5rdmtoolbox.database.file import _regex
        self.assertFalse(_regex(None, '*'))
        self.assertFalse(_regex('hallo', r'\d4'))
        self.assertFalse(_regex('hallo', 'hello'))

    def test_Folder(self):
        folder_dir = h5tbx.utils.generate_temporary_directory()
        sub_folder = folder_dir / 'sub_folder'
        sub_folder.mkdir()

        with h5tbx.File(folder_dir / 'f1.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with h5tbx.File(folder_dir / 'f2.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with h5tbx.File(folder_dir / sub_folder / 'f3.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with self.assertRaises(ValueError):
            h5tbx.database.Folder('here')
        fd = h5tbx.database.Folder(folder_dir, rec=False)
        self.assertEqual(2, len(list(fd.filenames)))

        self.assertEqual(2, len(fd.find({'long_name': 'long name 1'})))

        fdr = h5tbx.database.Folder(folder_dir, rec=True)
        self.assertEqual(3, len(list(fdr.filenames)))

    def test_Files(self):
        fnames = []
        with File() as h51:
            h51.create_dataset('ds', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            fnames.append(h51.filename)

            with File() as h52:
                h52.create_dataset('ds', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
                fnames.append(h52.filename)

                with Files(fnames) as h5s:
                    self.assertIsInstance(h5s['ds'], H5Objects)
                    self.assertEqual(h5s['ds'].basenames, ['ds', 'ds'])
                    self.assertEqual(h5s['ds'].shapes, ((1, 2, 3), (4, 2, 3)))
                    self.assertEqual(h5s['ds'].ndims, (3, 3))
                    self.assertIsInstance(h5s['ds'][:], DatasetValues)
                    self.assertIsInstance(h5s['ds'][0, :, 0].to_dataframe(), pd.DataFrame)
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

    def test_numerical(self):
        with h5tbx.File() as h5:
            h5.create_dataset('a1', shape=(1, 2, 3), attrs=dict(a=1))
            h5.create_dataset('a2', shape=(1, 2, 3), attrs=dict(a=2))
            h5.create_dataset('a3', shape=(1, 2, 3), attrs=dict(a=3))
            h5.create_dataset('a4', shape=(1, 2, 3), attrs=dict(a=4))
            h5.create_dataset('b5', shape=(1, 2, 3), attrs=dict(b=5))
            h5.create_dataset('b6', shape=(1, 2, 3), attrs=dict(b=6))

            self.assertEqual(h5.find({'a': None}), [])
            self.assertEqual(h5.find({'a': ''}), [])

            self.assertEqual(h5.find_one({'a': None}), None)

            self.assertListEqual(h5.find({'a': 1}), [h5['a1']])  # __eq__
            self.assertEqual(h5.find_one({'a': 1}), h5['a1'])  # __eq__

            self.assertEqual(h5.find({'a': {'$lt': 2}}), [h5['a1'], ])  # $lt
            self.assertEqual(h5.find_one({'a': {'$lt': 2}}), h5['a1'])  # $lt

            self.assertEqual(sorted(h5.find({'a': {'$lt': 3}})), sorted([h5['a1'], h5['a2'], ]))  # $lt
            self.assertIn(h5.find_one({'a': {'$lt': 3}}), [h5['a1'], h5['a2']])  # $lt

            self.assertEqual(h5.find({'a': {'$lte': 1}}), [h5['a1'], ])  # $lte
            self.assertEqual(h5.find_one({'a': {'$lte': 1}}), h5['a1'])  # $lte

            self.assertEqual(sorted(h5.find({'a': {'$lte': 2}})), [h5['a1'], h5['a2'], ])  # $lte
            self.assertIn(h5.find_one({'a': {'$lte': 2}}), [h5['a1'], h5['a2'], ])  # $lte

            self.assertEqual(h5.find({'a': {'$gt': 3}}), [h5['a4'], ])  # $gt
            self.assertEqual(h5.find_one({'a': {'$gt': 3}}), h5['a4'])  # $gt

            self.assertEqual(h5.find({'a': {'$gte': 4}}), [h5['a4'], ])  # $gte
            self.assertEqual(h5.find_one({'a': {'$gte': 4}}), h5['a4'])  # $gte

            self.assertEqual(sorted(h5.find({'a': {'$gte': 3}})), [h5['a3'], h5['a4'], ])  # $gte
            self.assertIn(h5.find_one({'a': {'$gte': 3}}), [h5['a3'], h5['a4'], ])  # $gte

    def test_lazy(self):
        with h5tbx.File() as h5:
            h5.create_group('g1', attrs={'a': 1, 'b': 2})
            h5.create_group('g2', attrs={'a': -12, 'b': 2})
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(a=99, b=100))
            h5.create_dataset('ds2', shape=(1, 2, 3), attrs=dict(a=2))
        r = h5tbx.database.File(h5.hdf_filename).find_one({'a': {'$gte': 80}})
        self.assertIsInstance(r, h5tbx.database.lazy.LDataset)
        self.assertIsInstance(r.attrs, h5tbx.database.lazy.LAttributeManager)
        self.assertEqual(r.attrs['a'], 99)
        self.assertEqual(r.attrs.keys(), r[()].attrs.keys())
        self.assertEqual(list(r.attrs.values()), list(r[()].attrs.values()))
        self.assertEqual(r.shape, (1, 2, 3))
        self.assertEqual(r.ndim, 3)

        with r as h5:
            self.assertIsInstance(h5, h5tbx.Dataset)

        r = h5tbx.database.File(h5.hdf_filename).find_one({'a': {'$gte': 0}}, '$group')
        self.assertIsInstance(r, h5tbx.database.lazy.LGroup)
        self.assertIsInstance(r.attrs, h5tbx.database.lazy.LAttributeManager)
        self.assertEqual(r.name, '/g1')
        self.assertEqual(r.basename, 'g1')

    def test_regex2(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(1, 2, 3), attrs=dict(units='', long_name='another long name 2'))
            h5.create_dataset('ds3', shape=(1, 2, 3), attrs=dict(units='', long_name='yet another long name 3'))

            self.assertEqual(h5.find_one({'long_name': {'$regex': 'long name 1'}}), h5['ds1'])
            self.assertEqual(h5.find_one({'long_name': {'$regex': 'does not exist'}}), None)
            self.assertIn(h5.find_one({'long_name': {'$regex': 'long name'}}), [h5['ds1'], h5['ds2'], h5['ds3']])
            self.assertEqual(sorted(h5.find({'long_name': {'$regex': '(.*)long name(.*)'}})),
                             [h5['ds1'], h5['ds2'], h5['ds3']])
            self.assertEqual(h5.find({'long_name': {'$regex': '(.*)long_name(.*)'}}),
                             [])

    def test_and_find(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds3', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_group('grps', attrs=dict(long_name='long name 1'))
            res = h5.find({'$basename': 'ds', 'long_name': 'long name 1'})
            self.assertEqual(res[0], h5['ds'])
            res = sorted(h5.find({'$shape': (1, 2, 3), 'long_name': 'long name 1'}, '$dataset'))
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0], h5['ds'])
            self.assertEqual(res[1], h5['ds2'])
            res = h5.find_one({'$shape': (1, 2, 3), 'long_name': 'long name 1'}, '$dataset')
            self.assertIn(res, [h5['ds'], h5['ds2']])
        res = h5tbx.database.File(h5.hdf_filename).find_one({'$basename': 'ds', 'long_name': 'long name 1'})
        self.assertEqual('ds', res.basename)

    def test_recursive_find(self):
        with h5tbx.File() as h5:
            gd = h5.create_group('trn_datacubes')
            gd.create_dataset('u', data=np.random.random((3, 5, 10, 20)))
            g = h5.create_group('monitors')
            g.create_dataset('pressure1', data=[1, 2, 3], attrs={'long_name': 'Pressure'})
            g.create_dataset('pressure2', data=[1, 2, 3], attrs={'long_name': 'Pressure'})

            self.assertEqual(gd.find({'long_name': 'Pressure'}, rec=True), [])
            self.assertEqual(gd.find({'long_name': 'Pressure'}, rec=False), [])
            self.assertEqual(gd.find({'$shape': (3, 5, 10, 20)}, rec=True, objfilter='$Dataset'), [gd.u])
            with self.assertRaises(AttributeError):
                gd.find({'$fail': (3, 5, 10, 20)}, objfilter='$Dataset', rec=True)

    def test_distinct(self):
        with h5tbx.File() as h5:
            gd = h5.create_group('trn_datacubes')
            gd.create_dataset('u', data=np.random.random((3, 5, 10, 20)))
            g = h5.create_group('monitors')
            g.create_dataset('pressure1', data=[1, 2, 3], attrs={'long_name': 'Pressure'})
            g.create_dataset('pressure2', data=[1, 2, 3], attrs={'long_name': 'Pressure'})

            self.assertEqual(h5.distinct('long_name', '$Dataset'), ['Pressure', ])
            self.assertEqual([(3,), (3, 5, 10, 20)], h5.distinct('$shape', '$Dataset'))
            self.assertEqual(sorted(['/trn_datacubes', '/monitors', '/']),
                             sorted(h5.distinct('$name', '$Group')))

    def test_getitem(self):
        fnames = []
        with File() as h51:
            h51.create_dataset('ds', data=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            fnames.append(h51.filename)

        with File() as h52:
            h52.create_dataset('ds', data=(4, 5, 6), attrs=dict(units='', long_name='long name 2'))
            fnames.append(h52.filename)

    def test_pfind(self):
        folder_dir = h5tbx.utils.generate_temporary_directory()
        sub_folder = folder_dir / 'sub_folder'
        sub_folder.mkdir()

        with h5tbx.File(folder_dir / 'f1.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with h5tbx.File(folder_dir / 'f2.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with h5tbx.File(folder_dir / sub_folder / 'f3.hdf', 'w') as h5:
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
            h5.create_dataset('ds3', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 3'))

        with self.assertRaises(ValueError):
            h5tbx.database.Folder('here')
        fd = h5tbx.database.Folder(folder_dir, rec=False)

        res = fd.find({'long_name': 'long name 1'})
        self.assertEqual(2, len(res))

        pres = fd.pfind({'long_name': 'long name 1'})

        self.assertEqual(sorted([r.filename for r in res]), sorted([r.filename for r in pres]))
        self.assertEqual(sorted([r.name for r in res]), sorted([r.name for r in pres]))

        pres = fd.pfind({'long_name': 'long name 1'}, nproc=2)

        self.assertEqual(sorted([r.filename for r in res]), sorted([r.filename for r in pres]))
        self.assertEqual(sorted([r.name for r in res]), sorted([r.name for r in pres]))

        pres = fd.pfind({'long_name': 'long name 1'}, nproc=1)

        self.assertEqual(sorted([r.filename for r in res]), sorted([r.filename for r in pres]))
        self.assertEqual(sorted([r.name for r in res]), sorted([r.name for r in pres]))
