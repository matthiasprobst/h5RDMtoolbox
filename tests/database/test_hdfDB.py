"""Test the mongoDB interface"""
import h5py
import numpy as np
import types
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import databases
from h5rdmtoolbox.databases import hdfdb


class TestHDFDB(unittest.TestCase):

    def test_insert(self):
        with h5py.File(h5tbx.utils.generate_temporary_filename(suffix='.hdf'),
                       'w') as h5:
            gdb = hdfdb.ObjDB(h5['/'])
            with self.assertRaises(NotImplementedError):
                gdb.insert_dataset(None)
            with self.assertRaises(NotImplementedError):
                gdb.insert_group(None)

    def test_find_one(self):
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
            self.assertIsInstance(single_res, database.lazy.LDataset)
            self.assertEqual(single_res.basename, 'dataset')

            # check $gt, ... operators:
            single_res = gdb_root.find_one({'a': {'$gt': 0}}, recursive=True)
            self.assertTrue(single_res.attrs['a'] > 0)

            single_res = gdb_root.find_one({'a': {'$gte': 0}}, recursive=True)
            self.assertTrue(single_res.attrs['a'] >= 0)

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
            self.assertIsInstance(multiple_results, types.GeneratorType)

            multiple_results = list(multiple_results)
            self.assertEqual(len(multiple_results), 2)
            self.assertIsInstance(multiple_results[0], h5tbx.databases.lazy.LHDFObject)

            multiple_results = gdb_root.find({'b': 1}, recursive=True)
            self.assertIsInstance(multiple_results, types.GeneratorType)
            self.assertEqual(len(list(multiple_results)), 0)

            multiple_results = gdb_root.find({'b': 2}, recursive=True)
            self.assertIsInstance(multiple_results, types.GeneratorType)
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
