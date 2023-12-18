"""Test the mongoDB interface"""
import h5py
import numpy as np
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import layout
from h5rdmtoolbox.database import hdfdb


class TestCore(unittest.TestCase):

    def test_eq(self):
        lay = layout.Layout()
        spec1 = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        spec2 = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)  # return spec1 object!
        self.assertEqual(spec1, spec2)
        self.assertEqual(spec1, spec1)  # same id
        self.assertNotEqual(spec1, None)
        self.assertNotEqual(spec1, 1)
        self.assertNotEqual(spec1, 'a')
        self.assertNotEqual(spec1, [])
        self.assertNotEqual(spec1, {})
        self.assertNotEqual(spec1, set())
        self.assertNotEqual(spec1, lay)

        spec3 = lay.add(hdfdb.FileDB.find, flt={'$name': '/v'}, n=2)
        self.assertNotEqual(spec1, spec3)

        spec_sub_1 = spec1.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        self.assertNotEqual(spec1, spec_sub_1)

    def test_number_of_datasets(self):
        filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            ds = h5.create_dataset('u', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/b/c/u', shape=(3, 4), dtype='float64')

            lay = layout.Layout()
            spec_number_of_specific_datasets = lay.add(
                hdfdb.FileDB.find,
                flt={'$name': {'$regex': '.*/u$'}}, n=2, recursive=True,
                comment='/u exists'
            )
            res = lay.validate(h5)
            self.assertFalse(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 0)

            lay = layout.Layout()
            spec_number_of_specific_datasets = lay.add(
                hdfdb.FileDB.find,
                flt={'$name': {'$regex': '.*/u$'}}, n=1, recursive=True,
                comment='/u exists'
            )
            res = lay.validate(h5)
            self.assertTrue(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 0)

            self.assertEqual(lay.specifications[0].n_calls, 1)
            lay.reset()
            self.assertEqual(lay.specifications[0].n_calls, 0)
            res = lay.validate(h5.filename)
            self.assertTrue(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 0)

            # self.assertTrue(spec1.failed)

    def test_all_dtypes(self):
        filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            ds = h5.create_dataset('u', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/u', shape=(3, 4), dtype='float64')
            h5.create_dataset('a/v', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/b/c/u', shape=(3, 4), dtype='float64')

            lay = layout.Layout()
            spec_all_ds = lay.add(hdfdb.FileDB.find,
                                  comment='Any dataset',
                                  n=None,
                                  flt={'$shape': {'$exists': True}},
                                  objfilter='dataset')  # all datasets
            spec_all_ds_are_float32 = spec_all_ds.add(hdfdb.FileDB.find_one,
                                                      comment='Is float32',
                                                      flt={'$dtype': np.dtype(
                                                          '<f4')})  # applies all these on spec_all_ds results
            with self.assertRaises(RuntimeError):
                lay(h5)

            res = lay.validate(h5)
            self.assertEqual(spec_all_ds_are_float32.n_calls, 4)
            self.assertEqual(spec_all_ds_are_float32.n_fails, 2)
            self.assertEqual(spec_all_ds_are_float32.n_successes, 2)

            self.assertFalse(res.is_valid())
            self.assertEqual(len(res.list_of_failed_specs), 1)
