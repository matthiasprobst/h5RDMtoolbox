"""Test the mongoDB interface"""
import h5py
import numpy as np
import sys
import unittest
from io import StringIO
from tabulate import tabulate

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import layout
from h5rdmtoolbox.database import hdfdb
from h5rdmtoolbox.layout.core import is_single_result


class TestCore(unittest.TestCase):

    def test_number_of_results(self):
        """Testing if the number of required results is handled correctly."""
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('a', shape=(3, 4), dtype='float32')
            h5.create_dataset('b', shape=(3, 4), dtype='float64')
            h5.create_dataset('c', shape=(3, 4, 5), dtype='float32')

            # exactly 2 datasets must be ndim==2:
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n=2, description='2D datasets')
            res = lay.validate(h5)
            self.assertFalse(spec.failed)
            self.assertTrue(res.is_valid())

            # exactly 2 datasets must be ndim==1:
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n=1, description='2D datasets')
            res = lay.validate(h5)
            self.assertTrue(spec.failed)
            self.assertFalse(res.is_valid())

            # at least 2 datasets must be ndim==2:
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n={'$gt': 1}, description='2D datasets')
            res = lay.validate(h5)
            self.assertFalse(spec.failed)
            self.assertTrue(res.is_valid())

            # at least 3 datasets must be ndim==2:
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n={'$gt': 2}, description='2D datasets')
            res = lay.validate(h5)
            self.assertTrue(spec.failed)
            self.assertFalse(res.is_valid())

            # at least 2 datasets must be ndim==2:
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n={'$gte': 2}, description='2D datasets')
            res = lay.validate(h5)
            self.assertFalse(spec.failed)
            self.assertTrue(res.is_valid())

            with self.assertRaises(ValueError):
                lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n=-2, description='2D datasets')

            with self.assertRaises(TypeError):
                lay.add(hdfdb.FileDB.find, flt={'$ndim': 2}, n=[1, 2, 3], description='2D datasets')

            # n=None --> query is optional
            lay = layout.Layout()
            spec = lay.add(hdfdb.FileDB.find, flt={'$ndim': 10}, n=None, description='2D datasets')
            res = lay.validate(h5)
            self.assertFalse(spec.failed)
            self.assertTrue(res.is_valid())

    def test_spec_properties(self):
        lay = layout.Layout()
        spec1 = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        spec1_copy = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        self.assertEqual(spec1, spec1_copy)
        self.assertFalse(spec1.__eq__(lay))
        self.assertEqual(spec1.called, False)
        with self.assertRaises(ValueError):
            spec1.n_successes

    # def test_units_exists(self):
    #     with h5tbx.File() as h5:
    #         ds = h5.create_dataset('a', shape=(3, 4), dtype='float32')
    #         ds.attrs['units'] = 'm/s'
    #     lay = layout.Layout()
    #     spec_all_dataset = lay.add(
    #         hdfdb.FileDB.find,
    #         flt={},
    #         objfilter='dataset',
    #         n={'$gte': 1},
    #         description='At least one dataset exists'
    #     )
    #     spec_all_dataset.add(hdfdb.FileDB.find,
    #                          flt={'units': {'$exists': True}},
    #                          n=1,
    #                          description='units exists')
    #     res = lay.validate(h5.hdf_filename)

    def test_alternative_specification(self):
        """Expecting exactly one u, but if not found, exactly one v."""
        lay = layout.Layout()
        main_spec = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1, description='u exists')
        main_spec.add_alternative(hdfdb.FileDB.find, flt={'$name': '/v'}, n=1, description='v exists if u does not')
        # with h5tbx.File() as h5:
        #     h5.create_dataset('u', shape=(3, 4), dtype='float32')
        #     res = lay.validate(h5)
        #     self.assertTrue(res.is_valid())

        # with h5tbx.File() as h5:
        #     # u does not exist, but v does
        #     h5.create_dataset('v', shape=(3, 4), dtype='float32')
        #     res = lay.validate(h5)
        #     self.assertTrue(res.is_valid())

        with h5tbx.File() as h5:
            # neither u nor v exist, should fail!
            h5.create_dataset('w', shape=(3, 4), dtype='float32')
            res = lay.validate(h5)
            res.print_summary(exclude_keys='target_name')
            self.assertFalse(res.is_valid())

        lay = layout.Layout()
        main_spec = lay.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=None)
        with self.assertRaises(ValueError):
            main_spec.add_alternative(hdfdb.FileDB.find, flt={'$name': '/v'}, n=1)

    def test_is_single_result(self):
        self.assertEqual(is_single_result(None), False)

        lay1 = layout.Layout()
        lay2 = layout.Layout()
        spec = lay1.add(hdfdb.ObjDB.find_one, flt={'$name': '/u'}, n=None)
        sub_spec = spec.add(hdfdb.ObjDB.find, flt={'$shape': (3, 4)}, n=None)

        # note, in the following find_one is used also for the sub_spec:
        spec2 = lay2.add(hdfdb.FileDB.find, flt={'$name': '/u'}, n=1)
        sub_spec2 = spec2.add(hdfdb.ObjDB.find_one, flt={'$shape': (3, 4)}, n=1)

        self.assertFalse(spec.is_valid())
        self.assertFalse(sub_spec.is_valid())
        self.assertEqual([], spec.get_valid())

        with h5tbx.File() as h5:
            h5.create_dataset('u', shape=(3, 4), dtype='float32')

            res = lay1.validate(h5)
            self.assertTrue(res.is_valid())
            res2 = lay2.validate(h5)
            self.assertTrue(res2.is_valid())

            self.assertTrue(spec.is_valid())
            self.assertTrue(sub_spec.is_valid())
            self.assertEqual([spec, sub_spec], spec.get_valid())

            summary = spec.get_summary()
            self.assertIsInstance(summary, list)
            self.assertIsInstance(summary[0], dict)
            self.assertIn('id', summary[0])
            self.assertEqual(len(summary), 2)

            self.assertEqual(len(sub_spec.get_summary()), 1)

            self.assertEqual(2, len(res.get_valid()))
            self.assertEqual(spec, res.get_valid()[0])
            self.assertEqual(sub_spec, res.get_valid()[1])

            self.assertIsInstance(res.get_summary(), list)
            self.assertIsInstance(res.get_summary()[0], dict)
            self.assertIn('id', res.get_summary()[0])
            self.assertEqual(str(spec.id), str(res.get_summary()[0]['id']))

    def test_print_summary(self):
        out = StringIO()
        sys.stdout = out
        lay = layout.Layout()
        spec = lay.add(hdfdb.ObjDB.find_one, flt={'$name': '/u'}, n=None)
        with h5tbx.File(name=None, mode='w') as h5:
            ds = h5.create_dataset('u', shape=(3, 4), dtype='float32')
            res = lay.validate(h5)
        res.print_summary()

        out_str = tabulate(res.get_summary(), headers='keys', tablefmt='psql')
        self.assertEqual(out.getvalue(), f'\nSummary of layout validation\n{out_str}\n--> Layout is valid\n')

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
                description='/u exists'
            )
            res = lay.validate(h5)
            self.assertFalse(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 0)

            lay = layout.Layout()
            spec_number_of_specific_datasets = lay.add(
                hdfdb.FileDB.find,
                flt={'$name': {'$regex': '.*/u$'}}, n=1, recursive=True,
                description='/u exists'
            )
            self.assertEqual(spec_number_of_specific_datasets.description, '/u exists')
            res = lay.validate(h5)
            self.assertTrue(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 1)

            self.assertEqual(lay.specifications[0].n_calls, 1)

            lay.reset()
            self.assertEqual(lay.specifications[0].n_calls, 0)
            res = lay.validate(h5.filename)
            self.assertTrue(spec_number_of_specific_datasets.failed)
            self.assertEqual(spec_number_of_specific_datasets.n_fails, 1)

    def test_all_dtypes(self):
        filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            ds = h5.create_dataset('f32', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/f64', shape=(3, 4), dtype='float64')
            h5.create_dataset('a/f32', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/b/c/f64', shape=(3, 4), dtype='float64')

            # there are 2 datasets with dtype float32 and 2 with float64
            # thus specification which checks float32 should fail twice

            lay = layout.Layout()
            spec_all_ds = lay.add(hdfdb.FileDB.find,
                                  description='Any dataset',
                                  n=None,  # optional
                                  recursive=True,
                                  flt={'$shape': {'$exists': True}},
                                  objfilter='dataset')  # all datasets
            spec_all_ds_are_float32 = spec_all_ds.add(
                hdfdb.FileDB.find,
                description='Is float32',
                flt={'$dtype': np.dtype('<f4')},
                n=1)  # applies all these on spec_all_ds results. So must be true per dataset (n=1)

            with self.assertRaises(RuntimeError):
                lay(h5)

            res = lay.validate(h5)
            res.print_summary()

            self.assertEqual(spec_all_ds.n_calls, 1)
            self.assertTrue(spec_all_ds.is_valid())

            self.assertEqual(spec_all_ds_are_float32.n_calls, 4)
            self.assertEqual(spec_all_ds_are_float32.n_fails, 2)  # 2 out of 4 failed
            self.assertEqual(spec_all_ds_are_float32.n_successes, 2)
            res.print_summary()
            self.assertFalse(res.is_valid())
            self.assertEqual(len(res.specifications), 1)

        # now a valid one
        with h5tbx.File() as h5:
            ds = h5.create_dataset('u', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/u', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/v', shape=(3, 4), dtype='float32')
            h5.create_dataset('a/b/c/u', shape=(3, 4), dtype='float32')

            res = lay.validate(h5)
            self.assertTrue(res.is_valid())
            self.assertTrue(spec_all_ds.is_valid())
            self.assertTrue(spec_all_ds_are_float32.is_valid())

    def test_layout_with_rdf_find(self):
        from h5rdmtoolbox import database
        lay = layout.Layout()
        spec = lay.add(database.rdf_find, rdf_predicate="https://schema.org/name", n=1)

        with h5tbx.File() as h5:
            h5.attrs['name', 'https://schema.org/name'] = 'test'

        res = lay.validate(h5.hdf_filename)
        self.assertTrue(res.is_valid())

        lay = layout.Layout()
        spec = lay.add(database.rdf_find, rdf_predicate="https://schema.org/firstName", n=1)

        with h5tbx.File() as h5:
            h5.attrs['name', 'https://schema.org/name'] = 'test'

        res = lay.validate(h5.hdf_filename)
        self.assertFalse(res.is_valid())

    def test_rebase(self):
        with h5tbx.File() as h5:
            h5.create_group('setup')
            h5['setup'].attrs['standard_name'] = 'Steady State'
            h5.create_dataset('TIME', data=[1, 2, 3], attrs={'units': 's'})

        lay = layout.Layout()
        spec = lay.add(hdfdb.FileDB.find,
                       flt={'standard_name': {'$in': ['Transient', 'Steady State']}},
                       n=1)
        spec.add(hdfdb.FileDB.find,
                 rebase=True,  # start search from the root
                 flt={'$name': '/TIME', 'units': 's', '$ndim': 1},
                 n=1)

        res = lay.validate(h5.hdf_filename)
        self.assertTrue(res.is_valid())
        with h5tbx.File() as h5:
            h5.create_group('setup')
            h5['setup'].attrs['standard_name'] = 'None of the above'
            h5.create_dataset('TIME', data=[1, 2, 3], attrs={'units': 's'})

        lay = layout.Layout()
        spec = lay.add(hdfdb.FileDB.find,
                       flt={'standard_name': {'$in': ['Transient', 'Steady State']}},
                       n=None)
        spec.add(hdfdb.FileDB.find,
                 rebase=True,  # start search from the root
                 flt={'$name': '/TIME', 'units': 's', '$ndim': 1},
                 n=1)

        res = lay.validate(h5.hdf_filename)
        self.assertTrue(res.is_valid())

        with h5tbx.File() as h5:
            h5.create_group('setup')
            h5['setup'].attrs['standard_name'] = 'Steady State'
            # h5.create_dataset('TIME', data=[1, 2, 3], attrs={'units': 's'})

        lay = layout.Layout()
        spec = lay.add(hdfdb.FileDB.find,
                       flt={'standard_name': {'$in': ['Transient', 'Steady State']}},
                       n=1)
        spec.add(hdfdb.FileDB.find,
                 rebase=True,  # start search from the root
                 flt={'$name': '/TIME', 'units': 's', '$ndim': 1},
                 n=1)

        res = lay.validate(h5.hdf_filename)
        self.assertFalse(res.is_valid())
