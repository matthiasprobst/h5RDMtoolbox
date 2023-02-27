import logging
import numpy as np
import pandas as pd
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper import set_loglevel
from h5rdmtoolbox.wrapper.h5attr import AttributeString
logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')


class TestCore(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use('default')

    def test_subclassstr_attrs(self):
        class MyString(str):
            def some_method(self):
                return True
        with h5tbx.H5File() as h5:
            h5.attrs['mystr'] = MyString('test')
            attr_str = h5.attrs['mystr']
            self.assertIsInstance(attr_str, AttributeString)
            h5.attrs['mystr'] = attr_str

            grp = h5.create_group('grp')
            grp.attrs['mystr'] = MyString('test')
            attr_str = grp.attrs['mystr']
            self.assertIsInstance(attr_str, AttributeString)
            grp.attrs['mystr'] = attr_str

    def test_from_csv(self):
        df = pd.DataFrame({'x': [1, 5, 10], 'y': [-3, 20, 0]})
        csv_filename = h5tbx.utils.generate_temporary_filename(suffix='.csv')
        df.to_csv(csv_filename)
        with h5tbx.H5File() as h5:
            h5.create_datasets_from_csv(csv_filename=csv_filename)

    def test_modify_static_properties(self):
        with h5tbx.H5File() as h5:
            ds_scale = h5.create_dataset('time', data=np.linspace(0, 1, 10),
                                         make_scale=True)
            ds = h5.create_dataset('grp/data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30),
                                   attach_scales=(ds_scale,))
            ds0 = ds[:]

            new_ds = ds.modify(chunks=(2, 5, 6))
            ds1 = new_ds[:]
            self.assertEqual(ds.chunks, (1, 20, 30))
            self.assertEqual(new_ds.chunks, (2, 5, 6))

            with self.assertWarns(UserWarning):
                # this will only raise a warning. nothing to change
                new_ds.modify(chunks=(2, 5, 6))

        self.assertTrue(np.all(ds1 == ds0))

        with h5tbx.H5File() as h5:
            ds = h5.create_dataset('data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30))
            ds0 = ds[:]

            new_ds = ds.modify(chunks=(2, 5, 6))
            ds1 = new_ds[:]

            self.assertEqual(ds.chunks, (1, 20, 30))
            self.assertEqual(new_ds.chunks, (2, 5, 6))
        self.assertTrue(np.all(ds1 == ds0))

        with h5tbx.H5File() as h5:
            ds = h5.create_dataset('data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30),
                                   dtype=int)
            new_ds = h5['/'].modify_dataset_properties(dataset=ds,
                                                       dtype=float)
            self.assertEqual(ds.dtype, int)
            self.assertEqual(new_ds.dtype, float)

            ds1 = new_ds[:]
            new_ds2 = h5['/'].modify_dataset_properties(dataset=new_ds,
                                                        name='data2')
            ds2 = new_ds2[:]
            self.assertEqual(new_ds2.name, '/data2')
            self.assertTrue('data' not in h5)
            self.assertTrue('data2' in h5)
            self.assertTrue(np.all(ds1 == ds2))

        with h5tbx.H5File() as h5:
            ds = h5.create_dataset('data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30),
                                   dtype='int16')
            new_ds = ds.modify(dtype='float32')
            self.assertEqual(ds.dtype, 'int16')
            self.assertEqual(new_ds.dtype, 'float32')

            ds1 = new_ds[:]
            new_ds2 = new_ds.rename('data2')
            ds2 = new_ds2[:]
            self.assertEqual(new_ds2.name, '/data2')
            self.assertTrue('data' not in h5)
            self.assertTrue('data2' in h5)
            self.assertTrue(np.all(ds1 == ds2))

    def test_conditional_slicing(self):
        with h5tbx.H5File() as h5:
            h5.create_dataset('time', data=range(0, 100), make_scale=True)
            h5.create_dataset('x', data=range(0, 100), make_scale=True)
            h5.create_dataset('y', data=range(0, 200), make_scale=True)
            h5.create_dataset('data', np.random.rand(100, 200, 100), attach_scale=('time', 'y', 'x'))
            self.assertEqual(h5.data[h5.data.time > 66, :, :].shape, (33, 200, 100))
            np.testing.assert_equal(h5.data.time > 66, np.arange(67, 100, 1))
            np.testing.assert_equal(h5.data.time >= 66, np.arange(66, 100, 1))
            np.testing.assert_equal(h5.data.time < 66, np.arange(0, 66, 1))
            np.testing.assert_equal(h5.data.time <= 66, np.arange(0, 67, 1))
            self.assertEqual(h5.data[h5.data.time == 66, :, :].shape, (1, 200, 100))
            np.testing.assert_equal(h5.data[h5.data.time == 66, :, :], h5.data.values[66, :, :].reshape(1, 200, 100))
            np.testing.assert_equal(h5.data.time == 66, np.array(66))
