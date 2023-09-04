import numpy as np
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper.core import File


class TestFileQuery(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_regex(self):
        from h5rdmtoolbox.database.file import _regex
        self.assertFalse(_regex(None, '*'))
        self.assertFalse(_regex('hallo', r'\d4'))
        self.assertFalse(_regex('hallo', 'hello'))

    def test_FileDB(self):
        fname1 = h5tbx.utils.generate_temporary_filename('.hdf', touch=True)
        fname2 = h5tbx.utils.generate_temporary_filename('.hdf', touch=True)
        tmp_dir = h5tbx.utils.generate_temporary_directory()
        fname3 = tmp_dir / 'tmpX.hdf'
        with h5tbx.File(fname3, 'w') as h5:
            pass
        fd = h5tbx.FileDB([fname1, fname2])
        self.assertEqual(fd.filenames, [fname1, fname2])
        fd = h5tbx.FileDB([fname1, fname2, tmp_dir])
        self.assertEqual(fd.filenames, [fname1, fname2, fname3])
        fd = h5tbx.FileDB([tmp_dir, ])
        self.assertEqual(fd.filenames, [fname3])
        f = h5tbx.FileDB(fname1)
        self.assertIsInstance(f, h5tbx.database.File)

        fname4 = tmp_dir / 'sub_grp/tmpX.hdf'
        fname4.parent.mkdir()
        with h5tbx.File(fname4, 'w') as h5:
            pass
        fd = h5tbx.FileDB(tmp_dir, rec=True)
        self.assertEqual(fd.filenames, [fname3, fname4])
        fd = h5tbx.FileDB([tmp_dir], rec=True)
        self.assertEqual(fd.filenames, [fname3, fname4])

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
        self.assertFalse(fd.rec)

        fdauto = h5tbx.FileDB(folder_dir, rec=False)
        self.assertIsInstance(fdauto, h5tbx.database.Folder)
        self.assertFalse(fdauto.rec)

        fdauto = h5tbx.FileDB(folder_dir, rec=True)
        self.assertIsInstance(fdauto, h5tbx.database.Folder)
        self.assertTrue(fdauto.rec)

        self.assertEqual(2, len(list(fd.filenames)))
        self.assertEqual(2, len(fd))
        self.assertEqual(fd.filenames[0], fd[0].filename)
        self.assertEqual(fd.filenames[0], fd.find_one({'$basename': 'ds1'}).filename)
        self.assertEqual(fd.filenames[0], fd.find_one({'$basename': 'ds1'}).filename)

        self.assertEqual(2, len(fd.find({'long_name': 'long name 1'})))

        fdr = h5tbx.database.Folder(folder_dir, rec=True)
        self.assertEqual(3, len(list(fdr.filenames)))

        res = fd.find_one_per_file({'$basename': {'$regex': 'ds[0-9]'}})
        self.assertEqual(2, len(res))

    def test_chained_find(self):
        with h5tbx.File() as h5:
            g = h5.create_group('grp1')
            g.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))

            r = h5.find_one({'$basename': 'grp1'}).find_one({'$basename': 'ds1'})
            self.assertEqual(r.name, '/grp1/ds1')

            r = h5.find({'$basename': 'grp1'})

            r = r.find_one({'$basename': 'ds1'})
            self.assertEqual(r.name, '/grp1/ds1')

        lazy_results = h5tbx.FileDB(h5.hdf_filename).find({'$basename': 'grp1'})
        r = h5tbx.database.file.ResultList(lazy_results).find_one({'$basename': 'ds1'})
        self.assertEqual(r.name, '/grp1/ds1')

        lazy_results = h5tbx.FileDB(h5.hdf_filename).find({'$basename': 'grp1'})
        r = h5tbx.database.file.ResultList(lazy_results).find({'$basename': 'ds1'})
        self.assertEqual(r[0].name, '/grp1/ds1')

        r = lazy_results.find_one({'$basename': 'non-existent'})
        self.assertTrue(r is None)

    def test_math_operators(self):
        from h5rdmtoolbox.database.file import _pass, _mean
        self.assertEqual(None, _pass(np.array([1, 2, 3]), 1))
        self.assertEqual(None, _mean(np.array(['hello', 'world'], dtype='S'), 1))

    def test_chained_find2(self):
        with h5tbx.File() as h5:
            h5.write_iso_timestamp(name='timestamp',
                                   dt=None)  # writes the current date time in iso format to the attribute
            h5.attrs['project'] = 'tutorial'
            h5.create_dataset('velocity', data=[1, 2, -1], attrs=dict(units='m/s', standard_name='x_velocity'))
            g = h5.create_group('group1')
            g.create_dataset('velocity', data=[4, 0, -3, 12, 3], attrs=dict(units='m/s', standard_name='x_velocity'))
            g = h5.create_group('group2')
            g.create_dataset('velocity', data=[12, 11.3, 4.6, 7.3, 8.1],
                             attrs=dict(units='m/s', standard_name='x_velocity'))
            g.create_dataset('z', data=5.4, attrs=dict(units='m', standard_name='z_coordinate'))
            h5.dump()
            filename = h5.hdf_filename
        # find the dataset "z". It is 0D with data=5.4
        results = h5tbx.FileDB(filename).find({'standard_name': 'z_coordinate'}).find({'$eq': 5.4})
        self.assertEqual(1, len(results))

    def test_Files(self):
        fnames = []
        with File() as h51:
            h51.create_dataset('ds', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            fnames.append(h51.hdf_filename)

            with File() as h52:
                h52.create_dataset('ds', shape=(4, 2, 3), attrs=dict(units='', long_name='long name 2'))
                fnames.append(h52.hdf_filename)

                with h5tbx.FileDB(fnames) as h5s:
                    self.assertIsInstance(h5s, h5tbx.database.Files)
                    self.assertEqual(2, len(h5s['ds']))
                    self.assertIsInstance(h5s['ds'][0], h5tbx.Dataset)
                    self.assertTrue(len(h5s.filenames) == 2)
                    with self.assertRaises(TypeError):
                        h5s.find(2)
                    res = h5s.find({'$basename': 'ds'})
                    self.assertEqual(sorted([h51.ds, h52.ds]), sorted(res))
                    res = h5s.find({'$basename': 'none'})
                    self.assertEqual(res, [])
                    res = h5s.find_one({'$basename': 'ds'})
                    self.assertEqual(h51.ds, res)

    def test_find_shortcuts(self):
        """find method shortcuts tests"""
        with h5tbx.File() as h5:
            h5.write_iso_timestamp(name='timestamp',
                                   dt=None)  # writes the current date time in iso format to the attribute
            h5.attrs['project'] = 'tutorial'
            h5.create_dataset('velocity', data=[1, 2, -1], attrs=dict(units='m/s', standard_name='x_velocity'))
            g = h5.create_group('group1')
            g.create_dataset('velocity', data=[4, 0, -3, 12, 3], attrs=dict(units='m/s', standard_name='x_velocity'))
            g = h5.create_group('group2')
            g.create_dataset('velocity', data=[12, 11.3, 4.6, 7.3, 8.1],
                             attrs=dict(units='m/s', standard_name='x_velocity'))
            h5.dump()
            filename = h5.hdf_filename

        res_v1 = h5tbx.database.File(filename).find({'standard_name': {'$regex': '.*'}}, '$dataset')
        res_v2 = h5tbx.database.File(filename).find('standard_name', '$dataset')
        for r1, r2 in zip(sorted(res_v1), sorted(res_v2)):
            self.assertEqual(r1, r2)

        res_v1 = h5tbx.database.File(filename).find({'standard_name': {'$regex': '.*'},
                                                     'units': {'$regex': '.*'}}, '$dataset')
        res_v2 = h5tbx.database.File(filename).find(['standard_name', 'units'], '$dataset')
        for r1, r2 in zip(sorted(res_v1), sorted(res_v2)):
            self.assertEqual(r1, r2)

        with self.assertRaises(TypeError):
            h5tbx.database.File(filename).find(2, '$dataset')

        with self.assertRaises(TypeError):
            h5tbx.database.File(filename).find([2, 2], '$dataset')

    def test_compare_to_dataset_values(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                h5.create_dataset('u', data=4.5, attrs=dict(units='m/s', standard_name='x_velocity'))
                h5.create_dataset('v', data=13.5, attrs=dict(units='m/s', standard_name='y_velocity'))
                g = h5.create_group('group1')
                g.create_dataset('u', data=4.5, attrs=dict(units='m/s', standard_name='x_velocity'))
                g.create_dataset('v', data=13.5, attrs=dict(units='m/s', standard_name='y_velocity'))

                res = h5.find({'$eq': 4.5}, '$dataset', rec=False)
                self.assertEqual(res, [h5['u']])

                res = h5.find({'$eq': 4.5}, rec=False)
                self.assertEqual(res, [h5['u']])

                res = h5.find({'$eq': 13.5}, '$dataset', rec=False)
                self.assertEqual(res, [h5['v']])

                res = h5.find({'$gt': 12.5}, rec=False)
                self.assertEqual(res, [h5['v']])

                res = h5.find({'$gt': 0.5}, rec=False)
                self.assertEqual(sorted(res), sorted([h5['v'], h5['u']]))

                res = h5.find({'$lt': 20.5}, rec=False)
                self.assertEqual(sorted(res), sorted([h5['v'], h5['u']]))

                res = h5.find({'$lte': 13.5}, rec=False)
                self.assertEqual(sorted(res), sorted([h5['v'], h5['u']]))

                res = h5.find({'$eq': 4.5}, rec=True)
                self.assertEqual(sorted(res), sorted([h5['u'], h5['/group1/u']]))

                res = h5.find_one({'$eq': 4.5}, rec=True)
                self.assertEqual(res.basename, h5['u'].basename)

    def test_compare_to_dataset_values_2(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                h5.create_dataset('u', data=[1.2, 3.4, 4.5], attrs=dict(units='m/s', standard_name='x_velocity'))
                h5.create_dataset('v', data=[4.0, 13.5, -3.4], attrs=dict(units='m/s', standard_name='y_velocity'))

                res = h5.find_one({'$eq': [1.2, 3.4, 4.5]}, rec=False)
                self.assertEqual(res.basename, h5['u'].basename)
                res = h5.find({'$eq': [1.2, 3.4, 4.5]}, rec=False)
                self.assertEqual(res[0].basename, h5['u'].basename)
                res = h5.find({'$eq': [1.2, 3.4, 4.0]}, rec=False)
                self.assertEqual(0, len(res))

    def test_compare_to_dataset_values_mean(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                h5.create_dataset('u', data=[1.2, 3.4, 4.5], attrs=dict(units='m/s', standard_name='x_velocity'))
                h5.create_dataset('v', data=[4.0, 13.5, -3.4], attrs=dict(units='m/s', standard_name='y_velocity'))
                res = h5.find({'$eq': {'$mean': np.mean([1.2, 3.4, 4.5])}}, rec=False)
                self.assertEqual(1, len(res))
                self.assertEqual(res[0].basename, h5['u'].basename)

    def test_compare_to_dataset_values_mean_combined(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                h5.create_dataset('u', data=[1.2, 3.4, 4.5], attrs=dict(units='m/s', standard_name='x_velocity'))
                h5.create_dataset('z', data=[1.2, 3.4, 4.5], attrs=dict(units='m/s', standard_name='z_velocity'))
                h5.create_dataset('v', data=[4.0, 13.5, -3.4], attrs=dict(units='m/s', standard_name='y_velocity'))

                res = h5.find({'standard_name': 'x_velocity',
                               '$eq': {'$mean': np.mean([1.2, 3.4, 4.5])}}, rec=False)

                self.assertEqual(1, len(res))
                self.assertEqual(res[0].basename, h5['u'].basename)

    def test_compare_to_dataset_values_range(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                h5.create_dataset('u', data=4.5, attrs=dict(units='m/s', standard_name='x_velocity'))
                h5.create_dataset('v', data=13.5, attrs=dict(units='m/s', standard_name='y_velocity'))

                res = h5.find({'$gt': 10.0, '$lt': 12.7}, rec=False)
                self.assertEqual(0, len(res))

                res = h5.find({'$gt': 10.0, '$lt': 13.7}, rec=False)
                self.assertEqual(1, len(res))
                self.assertEqual('v', res[0].basename)

    def test_numerical_attrs(self):
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
        self.assertTrue(h5tbx.database.lazy.lazy(None) is None)
        with self.assertRaises(TypeError):
            h5tbx.database.lazy.lazy(3.4)

        with h5tbx.File() as h5:
            h5.create_group('grp', attrs={'a': 1, 'b': 2})
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(a=99, b=100))
        self.assertIsInstance(h5tbx.database.lazy.lazy([h5.hdf_filename, 'ds1']),
                              h5tbx.database.lazy.LDataset)
        self.assertIsInstance(h5tbx.database.lazy.lazy([h5.hdf_filename, 'grp']),
                              h5tbx.database.lazy.LGroup)

        with h5tbx.File() as h5:
            h5.create_group('g1', attrs={'a': 1, 'b': 2})
            h5.create_group('g2', attrs={'a': -12, 'b': 2})
            h5.create_dataset('ds1', shape=(1, 2, 3), attrs=dict(a=99, b=100))
            h5.create_dataset('ds2', shape=(1, 2, 3), attrs=dict(a=2))
            h5.create_group('/a/b/c/d', attrs={'is_subgroup': True})
        r = h5tbx.database.File(h5.hdf_filename).find_one({'a': {'$gte': 80}})
        self.assertIsInstance(r, h5tbx.database.lazy.LDataset)
        self.assertIsInstance(r.attrs, dict)
        self.assertEqual(r.attrs['a'], 99)
        with h5tbx.set_config(add_provenance=False):
            self.assertEqual(r.attrs.keys(), r[()].attrs.keys())
            self.assertEqual(list(r.attrs.values()), list(r[()].attrs.values()))
        self.assertEqual(r.shape, (1, 2, 3))
        self.assertEqual(r.ndim, 3)

        with r as h5:
            self.assertIsInstance(h5, h5tbx.Dataset)

        r = h5tbx.database.File(h5.hdf_filename).find_one({'a': {'$gte': 0}}, '$group')

        self.assertIsInstance(r, h5tbx.database.lazy.LGroup)
        self.assertEqual('', r.parentname)
        self.assertEqual([], r.parentnames)

        r_subgrp = h5tbx.database.File(h5.hdf_filename).find_one({'is_subgroup': True}, '$group')
        self.assertIsInstance(r_subgrp, h5tbx.database.lazy.LGroup)
        self.assertEqual('/a/b/c', r_subgrp.parentname)
        self.assertEqual(['a', 'b', 'c'], r_subgrp.parentnames)

        self.assertIsInstance(r.attrs, dict)
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

    def test_isel(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds2', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 1'))
            h5.create_dataset('ds3', shape=(1, 2, 3), attrs=dict(units='', long_name='long name 2'))

        self.assertTrue(h5tbx.database.File(h5.hdf_filename).find_one({}, '$dataset') is None)
        res = h5tbx.database.File(h5.hdf_filename).find({}, '$dataset')
        self.assertEqual(len(res), 3)

        self.assertTupleEqual((2, 3), res[0].isel(dim_0=0).shape)
        with self.assertRaises(KeyError):
            res[0].isel(z=0.3)
        self.assertTupleEqual((1, 3), res[0].isel(dim_1=0).shape)
        self.assertTupleEqual((1, 2), res[0].isel(dim_2=0).shape)
        self.assertTupleEqual((1,), res[0].isel(dim_1=0, dim_2=1).shape)
        self.assertEqual(1, res[0].isel(dim_2=2, dim_1=1).ndim)
        self.assertEqual(0, res[0].isel(dim_2=2, dim_1=1, dim_0=0).ndim)
        with self.assertRaises(IndexError):
            self.assertEqual(0, res[0].isel(dim_2=2, dim_1=1, dim_0=2).ndim)
        self.assertTupleEqual((1, 2, 2), res[0].isel(dim_2=slice(0, 2, 1)).shape)
        with self.assertRaises(ValueError):
            res[0].isel(dim_5=2)

    def test_sel(self):
        with h5tbx.File() as h5:
            h5.create_dataset('z', data=[2, 5, 10], make_scale=True)
            h5.create_dataset('ds1', data=[1, 2, 3], attrs=dict(units='', long_name='long name 1'),
                              attach_scales=('z',))

        res = h5tbx.database.File(h5.hdf_filename).find({'$basename': {'$regex': '^ds[0-3]'}}, '$dataset')
        self.assertEqual(len(res), 1)

        with self.assertRaises(ValueError):
            res[0].sel(z=0.2).shape
        self.assertTupleEqual((), res[0].sel(z=0.2, method='nearest').shape)
        self.assertTrue(res[0].sel(z=0.2, method='nearest')[()] == 1)
        self.assertTrue(res[0].sel(z=4.8, method='nearest')[()] == 2)
        self.assertTrue(res[0].sel(z=5.2, method='nearest')[()] == 2)
        self.assertTrue(res[0].sel(z=8.9, method='nearest')[()] == 3)

        with self.assertRaises(NotImplementedError):
            res[0].sel(z=9, method='closest')
