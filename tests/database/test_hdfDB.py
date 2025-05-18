"""Test the mongoDB interface"""

import unittest
from typing import List

import h5py
import numpy as np
import pint

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import database
from h5rdmtoolbox.database import hdfdb
from h5rdmtoolbox.database.hdfdb.query import _basename


class TestHDFDB(unittest.TestCase):

    def setUp(self):
        h5tbx.use(None)

    def test_find_str(self):
        with h5tbx.File(attrs=dict(title='my file')) as h5:
            self.assertEqual(h5.find('title')[0].name, '/')
            h5.create_dataset('temp', data=np.array([1, 2, 3]),
                              attrs=dict(standard_name='temperature', units='K'))
            h5.create_dataset('vel/u', data=np.array([1, 2, 3]),
                              attrs=dict(standard_name='velocity', units='m/s'))
            res = sorted(h5.find(['standard_name', 'units']))
            self.assertEqual(res[0].name, '/temp')
            self.assertEqual(res[1].name, '/vel/u')

    def test_find_in_files(self):
        with h5tbx.File(attrs=dict(name='root group')) as h51:
            h51.create_group('grp')
            h51.create_dataset('x', data=[10, 20, 30], make_scale=True)
            h51.create_dataset('dataset', data=np.array([1, 2, 3]),
                               attrs=dict(units='m/s'),
                               attach_scale='x')
            h51.find('units')

        with h5tbx.File() as h52:
            h52.create_group('grp', attrs=dict(name='grp name'))
            h52.create_dataset('dataset', data=np.array([3, 2, 1]),
                               attrs=dict(units='mm/s'))

        res = list(h5tbx.database.find([h51.hdf_filename, h52.hdf_filename],
                                       {'name': 'root group'}))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, '/')

        res = list(h5tbx.database.find([h51.hdf_filename, h52.hdf_filename],
                                       {'name': 'grp name'}, recursive=False))
        self.assertEqual(len(res), 1)

        res = list(h5tbx.database.find([h51.hdf_filename, h52.hdf_filename],
                                       {'name': 'grp name'}, recursive=True))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].name, '/grp')

        res = h5tbx.database.find_one([h51.hdf_filename, h52.hdf_filename],
                                      {'name': 'grp name'}, recursive=True)
        self.assertEqual(res.name, '/grp')

    def test_dtype_char(self):
        # find a string dataset
        with h5tbx.File() as h5:
            ds = h5.create_string_dataset('a string ds', data=['one', 'two', 'three'])
            gdb = hdfdb.ObjDB(h5['/'])
            res = gdb.find_one({'$dtype': {'$regex': 'S*'}},
                               objfilter='dataset',
                               recursive=False)
            self.assertEqual(res, ds)
            ds_name = ds.name
        fdb = hdfdb.FileDB(h5.hdf_filename)
        fdb.find_one({'$dtype': {'$regex': 'S*'}},
                     objfilter='dataset',
                     recursive=False)
        self.assertIsInstance(res, h5tbx.database.lazy.LDataset)
        self.assertEqual(res.name, ds_name)

        h5tbx.database.find_one(h5.hdf_filename, {'$dtype': {'$regex': 'S*'}},
                                objfilter='dataset',
                                recursive=False)
        self.assertIsInstance(res, h5tbx.database.lazy.LDataset)
        self.assertEqual(res.name, ds_name)

        with self.assertRaises(FileNotFoundError):
            hdfdb.FileDB.find_one('invalid_filename.filename',
                                  {'$dtype': {'$regex': 'S*'}},
                                  objfilter='dataset',
                                  recursive=False)

        res = hdfdb.FileDB.find_one(h5.hdf_filename,
                                    {'$dtype': {'$regex': 'S*'}},
                                    objfilter='dataset',
                                    recursive=False)
        self.assertIsInstance(res, h5tbx.database.lazy.LDataset)
        self.assertEqual(res.name, ds_name)

        res = hdfdb.FileDB.find(h5.hdf_filename,
                                {'$dtype': {'$regex': 'S*'}},
                                objfilter='dataset',
                                recursive=False)
        # res is a generator
        self.assertIsInstance(res, list)
        res = list(res)
        self.assertIsInstance(res, list)
        self.assertIsInstance(res[0], h5tbx.database.lazy.LDataset)
        self.assertEqual(res[0].name, ds_name)

        res = hdfdb.FileDB(h5.hdf_filename).find({'$dtype': {'$regex': 'S*'}},
                                                 objfilter='dataset',
                                                 recursive=False)
        self.assertIsInstance(res, list)
        self.assertIsInstance(res[0], h5tbx.database.lazy.LDataset)
        self.assertEqual(res[0].name, ds_name)

        # find a string dataset
        with h5tbx.File() as h5:
            h5.create_string_dataset('a string ds', data=['one', 'two', 'three'])
            ds = h5.create_dataset('num', data=2.4)
            print(str(ds.dtype))
            gdb = hdfdb.ObjDB(h5['/'])
            res = gdb.find({'$dtype': {'$regex': r'^(?!\|S|\|).*'}},  # does not starts with "|S" or "|"
                           objfilter='dataset',
                           recursive=False)
            self.assertEqual(list(res), [ds, ])

    def test_value_find(self):
        with h5tbx.File(mode='w') as h5:
            ds_random = h5.create_dataset('random', data=np.array([1, 2, 3]))
            ds_half = h5.create_dataset('half', data=0.5)
            gdb = hdfdb.ObjDB(h5['/'])
            res = gdb.find_one({'$eq': 0.5}, recursive=True)
            self.assertEqual(res.name, ds_half.name)
            with self.assertRaises(TypeError):
                gdb.find_one({'$gte', 0.5}, recursive=True)
            res = gdb.find_one({'$gte': 0.5}, recursive=True)
            self.assertEqual(res.name, ds_half.name)
            res = gdb.find_one({'$lte': 0.5}, recursive=True)
            self.assertEqual(res.name, ds_half.name)
            res = gdb.find_one({'$gt': 0.5}, recursive=True)
            self.assertTrue(res is None)
            res = gdb.find_one({'$lt': 0.5}, recursive=True)
            self.assertTrue(res is None)
            res = gdb.find_one({'$eq': np.array([1, 2, 3])}, recursive=True)
            self.assertEqual(res.name, ds_random.name)

    def test_find_shape(self):
        with h5tbx.File(mode='w') as h5:
            ds_random = h5.create_dataset('random', data=np.array([1, 2, 3]))
            ds_half = h5.create_dataset('half', data=0.5)

            gdb = hdfdb.ObjDB(h5['/'])

            with self.assertRaises(TypeError):
                gdb.find_one({'$shape', (3,)}, recursive=True)

            res = gdb.find_one({'$shape': (3,)}, recursive=True)
            self.assertEqual(res.name, ds_random.name)
            res = gdb.find({'$ndim': 1}, recursive=True)
            self.assertListEqual([r.name for r in res], [ds_random.name])

            res = gdb.find({'$ndim': {'$gt': 0}}, recursive=True)
            self.assertListEqual([r.name for r in res], [ds_random.name, ])

            res = gdb.find({'$ndim': {'$gte': 1}}, recursive=True)
            self.assertListEqual([r.name for r in res], [ds_random.name, ])

            res = gdb.find({'$ndim': {'$gte': 0}}, recursive=True)
            self.assertListEqual(sorted([r.name for r in res]), sorted([ds_random.name, ds_half.name]))

    def test_distinct_props(self):
        with h5tbx.File(mode='w') as h5:
            ds_random = h5.create_dataset('random', data=np.array([1, 2, 3]))
            ds_half = h5.create_dataset('half', data=0.5)

            gdb = hdfdb.ObjDB(h5['/'])
            res = gdb.distinct('$shape')
            self.assertListEqual(sorted(res), [(), (3,)])

            gdb = hdfdb.ObjDB(h5['/'])
            res = gdb.distinct('$ndim')
            self.assertListEqual(sorted(res), [0, 1])

    def test_find_one(self):
        with h5tbx.set_config(auto_create_h5tbx_version=False):
            with h5py.File(h5tbx.utils.generate_temporary_filename(suffix='.hdf'),
                           'w') as h5:
                h5.attrs['long_name'] = 'root group'
                grp = h5.create_group('grp')
                grp.attrs['a'] = 1
                grp.attrs['long_name'] = 'a group'
                ds = h5.create_dataset('dataset', shape=(2, 3), dtype='float64')
                ds.attrs['a'] = 1
                ds.attrs['b'] = 2
                grp.create_dataset('sub_grp_dataset', shape=(4,))

                dsdb = hdfdb.ObjDB(h5)

                res_only_dataset = dsdb.find({'$dtype': {'$exists': True}})
                self.assertEqual(len(list(res_only_dataset)), 2)

                del grp['sub_grp_dataset']

                grpdb = hdfdb.ObjDB(h5['grp'])
                res_is_dataset = grpdb.find_one({'$dtype': {'$exists': True}}, recursive=False)
                self.assertTrue(res_is_dataset is None)

                dsdb = hdfdb.ObjDB(h5['dataset'])
                res_is_dataset = dsdb.find_one({'$dtype': {'$exists': True}})
                self.assertTrue(res_is_dataset is not None)

                res = dsdb.find_one({'$dtype': np.dtype('<f8')}, objfilter='dataset')  # is float64
                self.assertEqual(res, ds)
                res = dsdb.find_one({'$dtype': np.dtype('<f4')}, objfilter='dataset')  # is float64
                self.assertEqual(res, None)

                gdb_grp = hdfdb.ObjDB(h5['grp'])
                res = dsdb.find_one({'$name': '/dataset'}, recursive=False)
                with res as res_ds:
                    self.assertEqual(res_ds, ds)

                res = dsdb.find_one({'units': {'$exists': True}}, recursive=False)
                self.assertTrue(res is None)

                ds.attrs['units'] = 'invalid units'

                res = dsdb.find_one({'units': {'$exists': True}}, recursive=False)
                self.assertFalse(res is None)

                single_res = gdb_grp.find_one({'a': 1}, recursive=False)
                self.assertIsInstance(single_res, database.lazy.LGroup)
                self.assertEqual(single_res.basename, 'grp')

                gdb_root = hdfdb.ObjDB(h5['/'])
                single_res = gdb_root.find_one({'a': 1}, objfilter=h5py.Dataset)
                self.assertIsInstance(single_res, database.lazy.LDataset)
                self.assertEqual(single_res.basename, 'dataset')

                gdb_root = hdfdb.ObjDB(h5['/'])
                single_res = gdb_root.find_one({'a': 1}, objfilter='dataset')
                self.assertIsInstance(single_res, database.lazy.LDataset)
                self.assertEqual(single_res.basename, 'dataset')

                single_res = gdb_root.find_one({'b': 2}, recursive=True)
                self.assertIsInstance(single_res, database.lazy.LDataset)
                self.assertEqual(single_res.basename, 'dataset')

                # check $exists operator:
                single_res = gdb_root.find_one({'long_name': {'$exists': True}},
                                               recursive=True)
                self.assertIsInstance(single_res, database.lazy.LGroup)
                self.assertTrue(single_res.basename in ('grp', ''))

                single_res = gdb_root.find_one({'long_name': {'$exists': False}},
                                               recursive=True)
                self.assertIsInstance(single_res, database.lazy.LHDFObject)
                self.assertEqual(single_res.basename, 'dataset')

                # check $gt, ... operators:
                single_res = gdb_root.find_one({'a': {'$gt': 0}}, recursive=True)
                self.assertTrue(single_res.attrs['a'] > 0)

                single_res = gdb_root.find_one({'a': {'$gte': 0}}, recursive=True)
                self.assertTrue(single_res.attrs['a'] >= 0)

    def test_find_dict_attr(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('grp')
            ds = h5.create_dataset('dataset', shape=(2, 3))
            ds.attrs['a'] = 1
            grp.attrs['a'] = 1
            grp.attrs['b'] = {'c': 2}
            gb = hdfdb.ObjDB(h5['/'])
            res = gb.find_one({'b.c': 2}, recursive=True)
            self.assertEqual(res.name, grp.name)
            res = gb.find({'a': 1}, recursive=True)
            self.assertListEqual(sorted([r.name for r in res]),
                                 sorted([grp.name, ds.name]))
            res = gb.find({'a': 1}, objfilter='dataset', recursive=True)
            self.assertListEqual(sorted([r.name for r in res]),
                                 sorted([ds.name, ]))

    def test_distinct(self):
        with h5tbx.File(mode='w') as h5:
            h5.attrs['tag'] = 'root'
            h5.create_dataset('dataset', data=np.array([1, 2, 3]),
                              attrs={'tag': 'dataset', 'units': 'm'})
            h5.create_dataset('dataset2', data=np.array([[1, 2, 3],
                                                         [1, 2, 3]]),
                              attrs={'tag': 'dataset', 'units': 'm/s'})
            grp = h5.create_group('grp')
            grp.attrs['tag'] = 'group'
            gb = hdfdb.ObjDB(h5['/'])
            res = gb.distinct('tag')
            self.assertListEqual(sorted(res), sorted(['root', 'dataset', 'group']))
            res = gb.distinct('units')
            self.assertListEqual(sorted(res), sorted(['m', 'm/s']))

            res = gb.distinct('units', objfilter='dataset')
            self.assertListEqual(sorted(res), sorted(['m', 'm/s']))

            res = gb.distinct('$ndim')
            self.assertListEqual(sorted(res), sorted([1, 2]))

            res = gb.distinct('$ndim', objfilter='dataset')
            self.assertListEqual(sorted(res), sorted([1, 2]))

    def test_regex(self):
        from h5rdmtoolbox.database.hdfdb.query import _regex
        self.assertFalse(_regex(None, 'b'))
        self.assertTrue(_regex('a', 'a'))
        self.assertTrue(_regex(b'a', 'a'))
        self.assertTrue(_regex(np.bytes_('a'), 'a'))

    def test_eq(self):
        from h5rdmtoolbox.database.hdfdb.query import _eq
        self.assertFalse(_eq(None, 'b'))
        self.assertTrue(_eq('a', 'a'))
        self.assertTrue(_eq(1, 1))
        self.assertFalse(_eq(1, 2))

    def test_lte(self):
        from h5rdmtoolbox.database.hdfdb.query import _lte
        self.assertFalse(_lte(None, 'b'))
        self.assertFalse(_lte('a', None))
        self.assertTrue(_lte(1, 2))
        self.assertTrue(_lte(1, 1))
        self.assertFalse(_lte(2, 1))

    def test_gte(self):
        from h5rdmtoolbox.database.hdfdb.query import _gte
        self.assertFalse(_gte(None, 'b'))
        self.assertFalse(_gte('a', None))
        self.assertTrue(_gte(2, 1))
        self.assertTrue(_gte(1, 1))
        self.assertFalse(_gte(1, 2))

    def test_lt(self):
        from h5rdmtoolbox.database.hdfdb.query import _lt
        self.assertFalse(_lt(None, 'b'))
        self.assertFalse(_lt('a', None))
        self.assertTrue(_lt(1, 2))
        self.assertFalse(_lt(1, 1))
        self.assertFalse(_lt(2, 1))

    def test_gt(self):
        from h5rdmtoolbox.database.hdfdb.query import _gt
        self.assertFalse(_gt(None, 'b'))
        self.assertFalse(_gt('a', None))
        self.assertTrue(_gt(2, 1))
        self.assertFalse(_gt(1, 1))
        self.assertFalse(_gt(1, 2))

    def test_basename(self):
        self.assertFalse(_basename(None, 'b'))
        self.assertFalse(_basename('a', None))
        self.assertTrue(_basename('/a', 'a'))
        self.assertTrue(_basename('/a/b', 'b'))
        self.assertTrue(_basename('/a/b/c', 'c'))
        self.assertFalse(_basename('/a/b/c', 'c/d'))
        self.assertFalse(_basename('/a/b/c', 'b'))
        self.assertFalse(_basename('/a/b/c', 'a'))
        self.assertFalse(_basename('/a/b/c', '/a/b/c'))

        with h5tbx.File() as h5:
            ds = h5.create_dataset('T1', data=4)
            res = h5.find_one({'$name': {'$basename': 'T1'}})
            self.assertEqual(res, ds)
            res = h5.find_one({'$basename': 'T1'})
            self.assertEqual(res, ds)

    def test_get_ndim(self):
        from h5rdmtoolbox.database.hdfdb.query import get_ndim
        self.assertEqual(0, get_ndim(5))
        self.assertEqual(0, get_ndim(np.array(5.4)))
        self.assertEqual(1, get_ndim(np.array([1, 2, 3])))
        self.assertEqual(2, get_ndim(np.array([[1, 2, 3]])))
        self.assertEqual(3, get_ndim(np.array([[[1, 2, 3]]])))

    def test_find(self):
        with h5py.File(h5tbx.utils.generate_temporary_filename(suffix='.hdf'),
                       'w') as h5:
            grp = h5.create_group('grp')
            grp.attrs['a'] = 1
            ds = h5.create_dataset('dataset', shape=(2, 3))
            ds.attrs['a'] = 1
            ds.attrs['b'] = 2

            gdb_root = hdfdb.ObjDB(h5)
            multiple_results = gdb_root.find({'a': 1}, recursive=True)
            self.assertIsInstance(multiple_results, list)

            multiple_results = h5tbx.database.find(h5, {'a': 1}, recursive=True)
            self.assertIsInstance(multiple_results, list)

            multiple_results = list(multiple_results)
            self.assertEqual(len(multiple_results), 2)
            self.assertIsInstance(multiple_results[0], h5tbx.database.lazy.LHDFObject)

            multiple_results = gdb_root.find({'b': 1}, recursive=True)
            self.assertIsInstance(multiple_results, list)
            self.assertEqual(len(list(multiple_results)), 0)

            multiple_results = gdb_root.find({'b': 2}, recursive=True)
            self.assertIsInstance(multiple_results, list)
            self.assertEqual(len(list(multiple_results)), 1)

    def test_filesDB_find_one(self):
        filename1 = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        filename2 = h5tbx.utils.generate_temporary_filename(suffix='.hdf')

        with h5py.File(filename1, 'w') as h5:
            grp = h5.create_group('grp')
            grp.attrs['a'] = 1
            grp.attrs['i am'] = 'a group 1'
            ds = h5.create_dataset('dataset', shape=(2, 3))
            ds.attrs['a'] = 1
            ds.attrs['b'] = 2
            ds.attrs['i am'] = 'a dataset'

        with h5py.File(filename2, 'w') as h5:
            grp = h5.create_group('grp')
            grp.attrs['a'] = 1
            grp.attrs['i am'] = 'a group 2'
            ds = h5.create_dataset('dataset', shape=(2, 3))
            ds.attrs['a'] = 1
            ds.attrs['b'] = 2
            ds.attrs['c'] = '3'
            ds.attrs['d'] = 4
            ds.attrs['i am'] = 'a dataset'

        self.assertTrue(filename1.exists())
        self.assertTrue(filename2.exists())

        filesdb = hdfdb.FilesDB([filename1, filename2])

        single_res = filesdb.find_one({'i am': 'a group 1'}, recursive=True)
        self.assertIsInstance(single_res, database.lazy.LGroup)
        self.assertEqual(single_res.filename, filename1)

        single_res = filesdb.find_one({'i am': 'a group 2'}, recursive=True)
        self.assertIsInstance(single_res, database.lazy.LGroup)
        self.assertEqual(single_res.filename, filename2)

        single_res = filesdb.find_one({'d': 4}, recursive=True)
        self.assertIsInstance(single_res, database.lazy.LDataset)
        self.assertEqual(single_res.filename, filename2)

        # multi_res = filesdb.find({'d': 4}, recursive=True)
        # self.assertIsInstance(multi_res, list)
        # multi_res = list(multi_res)
        # self.assertEqual(len(multi_res), 1)
        # self.assertIsInstance(multi_res[0], database.lazy.LDataset)
        # self.assertEqual(multi_res[0].filename, filename2)

    def test_filesDB_insert_filename(self):
        filename1 = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        filename2 = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        filesdb = hdfdb.FilesDB([filename1, ])
        self.assertListEqual(filesdb.filenames, [filename1, ])
        filesdb.insert_filename(filename2)
        self.assertListEqual(sorted(filesdb.filenames), sorted([filename1, filename2]))

    def test_filesDB_from_folder(self):
        folder = h5tbx.utils.generate_temporary_directory()
        filename1 = folder / 'f1.hdf'
        filename2 = folder / 'f2.hdf'
        filename3 = folder / 'f3.h5'

        for filename in [filename1, filename2, filename3]:
            with h5py.File(filename, 'w') as h5:
                pass

        subfolder = folder / 'sub'
        subfolder.mkdir(parents=True, exist_ok=True)
        filename4 = subfolder / 'f4.hdf'
        filename5 = subfolder / 'f5.hdf'
        filename6 = subfolder / 'f6.h5'

        for filename in [filename4, filename5, filename6]:
            with h5py.File(filename, 'w') as h5:
                pass

        fdb = hdfdb.FilesDB.from_folder(folder, hdf_suffixes='.hdf')
        self.assertEqual(len(fdb.filenames), 2)
        self.assertListEqual(sorted(fdb.filenames), sorted([filename1, filename2]))

        fdb = hdfdb.FilesDB.from_folder(folder, hdf_suffixes='.h5')
        self.assertEqual(len(fdb.filenames), 1)
        self.assertListEqual(sorted(fdb.filenames), sorted([filename3]))

        fdb = hdfdb.FilesDB.from_folder(folder, hdf_suffixes=['.h5', '.hdf'])
        self.assertEqual(len(fdb.filenames), 3)
        self.assertListEqual(sorted(fdb.filenames), sorted([filename1, filename2, filename3]))

        fdb = hdfdb.FilesDB.from_folder(folder, hdf_suffixes=['.h5', '.hdf'], recursive=True)
        self.assertEqual(len(fdb.filenames), 6)
        self.assertListEqual(sorted(fdb.filenames),
                             sorted([filename1, filename2, filename3, filename4, filename5, filename6]))

        fdb = hdfdb.FilesDB.from_folder(folder, hdf_suffixes=['.h5', ], recursive=True)
        self.assertEqual(len(fdb.filenames), 2)
        self.assertListEqual(sorted(fdb.filenames), sorted([filename3, filename6]))

    def test_find_rdf(self):
        from rdflib import FOAF
        with h5tbx.File() as h5:
            grp = h5.create_group('contact')
            grp.attrs['name', FOAF.firstName] = 'Matthias'
            grp.rdf.subject = 'https://example.org/Matthias'

            grp = h5.create_group('contact2')
            grp.attrs['name', FOAF.firstName] = 'John'
            grp.rdf.subject = 'https://example.org/John'

            h5.attrs['name', 'https://schema.org/name'] = 'test'
            res = h5.rdf.find(rdf_predicate='https://schema.org/name')
            self.assertEqual(res[0].name, '/')
            print(list(res))

        res = h5tbx.database.rdf_find(h5.hdf_filename, rdf_predicate='https://schema.org/name')
        print(list(res))

        # attribute search:
        res = h5tbx.database.find(h5.hdf_filename, flt=dict(name='test'))
        print(list(res))

        res = h5tbx.database.rdf_find(h5.hdf_filename, rdf_predicate=FOAF.firstName)
        res_list = sorted(list(res), key=lambda x: x.name)
        self.assertEqual(len(res_list), 2)
        self.assertEqual(res_list[0].name, '/contact')
        self.assertEqual(res_list[1].name, '/contact2')

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_predicate=FOAF.firstName,
                                      rdf_subject='https://example.org/Matthias')
        res_list = sorted(list(res), key=lambda x: x.name)
        self.assertEqual(len(res_list), 1)
        self.assertEqual(res_list[0].name, '/contact')

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_subject='https://example.org/Matthias')
        res_list = sorted(list(res), key=lambda x: x.name)
        self.assertEqual(len(res_list), 1)
        self.assertEqual(res_list[0].name, '/contact')

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_subject='https://example.org/John')
        res_list = sorted(list(res), key=lambda x: x.name)
        self.assertEqual(len(res_list), 1)
        self.assertEqual(res_list[0].name, '/contact2')

        res = h5tbx.database.rdf_find(h5.hdf_filename,
                                      rdf_predicate=FOAF.firstName,
                                      rdf_subject='https://example.org/John')
        res_list = sorted(list(res), key=lambda x: x.name)
        self.assertEqual(len(res_list), 1)
        self.assertEqual(res_list[0].name, '/contact2')

    def test_dtype_kind(self):
        with h5tbx.File() as h5:
            h5.create_string_dataset('strds', data='hallo')
            h5.create_dataset('f32', shape=(3, 4), dtype='float32')
            h5.create_dataset('f64', shape=(3, 4), dtype='float64')
            h5.create_dataset('i32', shape=(3, 4), dtype='int32')

            res = h5.find({'$dtype': lambda x: x.kind == 'S'})
            for r in res:
                self.assertEqual(r.name, '/strds')
            numerical_datasets = h5.find({'$dtype': lambda x: x.kind in ('f', 'i', 'u')})
            self.assertEqual(len(list(numerical_datasets)), 3)

    def test_custom_find(self):
        with h5tbx.File() as h5:
            h5.create_dataset('u', data=4.3, attrs={'units': 'm/s', 'standard_name': 'x_velocity'})
            h5.create_dataset('v', data=4.3, attrs={'units': 'm/s', 'standard_name': 'v_velocity'})  # invalid sn
            h5.create_dataset('w', data=4.3, attrs={'units': 'invalid',
                                                    'standard_name': 'z_velocity'})

            ureg = pint.UnitRegistry()

            def _validate_unit(units: str):
                if units is None:
                    return False

                if units in ('', ' '):
                    return True
                try:
                    ureg.parse_units(units)
                    return True
                except pint.UndefinedUnitError:
                    return False

            def _valid_standard_name(sn, list_of_sn: List[str]):
                return sn in list_of_sn

            res = h5.find({'units': lambda x: _validate_unit(x)})
            self.assertEqual(len(res), 2)

            res = h5.find({'standard_name': lambda x: _valid_standard_name(x, ['x_velocity',
                                                                               'y_velocity',
                                                                               'z_velocity'])})
            self.assertEqual(len(res), 2)

    def test_in(self):
        with h5tbx.File() as h5:
            h5.attrs['standard_name'] = 'Steady State'
            res = h5.find({'standard_name': {'$in': ['Transient', 'Steady State']}})
            self.assertEqual(len(res), 1)
        with h5tbx.File() as h5:
            h5.attrs['standard_name'] = 'Transient'
            res = h5.find({'standard_name': {'$in': ['Transient', 'Steady State']}})
            self.assertEqual(len(res), 1)
        with h5tbx.File() as h5:
            h5.attrs['standard_name'] = 'Transient2'
            res = h5.find({'standard_name': {'$in': ['Transient', 'Steady State']}})
            self.assertEqual(len(res), 0)
