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

    def test_lower(self):
        self.assertEqual(h5tbx.core.Lower('Hello'), 'hello')
        self.assertIsInstance(h5tbx.core.lower('Hello'), h5tbx.core.Lower)

    def test_File(self):
        self.assertEqual(str(h5tbx.File), "<class 'h5rdmtoolbox.File'>")
        with h5tbx.File() as h5:
            self.assertEqual(h5.__str__(), "<class 'h5rdmtoolbox.File' convention: default>")
        self.assertEqual(h5tbx.File.Dataset(), h5tbx.core.Dataset)
        self.assertEqual(h5tbx.File.Group(), h5tbx.core.Group)

    def test_Files(self):
        with h5tbx.File() as h5:
            f1 = h5.hdf_filename
        with h5tbx.File() as h5:
            f2 = h5.hdf_filename
        with self.assertRaises(ValueError):
            with h5tbx.Files([f1, ]):
                pass
        with h5tbx.Files([f1, f2]) as h5:
            self.assertEqual(str(h5), "<Files (2 files)>")
            self.assertIsInstance(h5[0], h5tbx.wrapper.core.File)
            self.assertIsInstance(h5[1], h5tbx.wrapper.core.File)
        with h5tbx.Files([f1, f2], file_instance=h5tbx.wrapper.core.File) as h5:
            self.assertEqual(str(h5), "<Files (2 files)>")
            self.assertIsInstance(h5[0], h5tbx.wrapper.core.File)
            self.assertIsInstance(h5[1], h5tbx.wrapper.core.File)

    def test_subclassstr_attrs(self):
        class MyString(str):
            def some_method(self):
                return True

        with h5tbx.File() as h5:
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
        df = pd.DataFrame({'x': [1, 5, 10, 0], 'y': [-3, 20, 0, 11.5]})
        csv_filename1 = h5tbx.utils.generate_temporary_filename(suffix='.csv')
        df.to_csv(csv_filename1, index=None)

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=csv_filename1)
            self.assertEqual(h5['x'].shape, (4,))
            self.assertEqual(h5['y'].shape, (4,))
            np.testing.assert_equal(h5['x'][:], np.array([1, 5, 10, 0]))
            np.testing.assert_equal(h5['y'][:], np.array([-3, 20, 0, 11.5]))

        with h5tbx.File() as h5:
            h5.create_dataset_from_csv(csv_filename=csv_filename1)
            self.assertEqual(h5['x'].shape, (4,))
            self.assertEqual(h5['y'].shape, (4,))
            np.testing.assert_equal(h5['x'][:], np.array([1, 5, 10, 0]))
            np.testing.assert_equal(h5['y'][:], np.array([-3, 20, 0, 11.5]))

        csv_filename2 = h5tbx.utils.generate_temporary_filename(suffix='.csv')
        df.to_csv(csv_filename2, index=None)

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='concatenate')
            self.assertEqual(h5['x'].shape, (8,))
            self.assertEqual(h5['y'].shape, (8,))

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        axis=0)
            self.assertEqual(h5['x'].shape, (2, 4))
            self.assertEqual(h5['y'].shape, (2, 4))
            np.testing.assert_equal(h5['x'][:], np.array([[1, 5, 10, 0], [1, 5, 10, 0]]))
            np.testing.assert_equal(h5['y'][:], np.array([[-3, 20, 0, 11.5], [-3, 20, 0, 11.5]]))

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='stack',
                                        axis=-1)
            self.assertEqual(h5['x'].shape, (4, 2))
            self.assertEqual(h5['y'].shape, (4, 2))

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='stack',
                                        axis=0,
                                        shape=(2, 2))
            self.assertEqual(h5['x'].shape, (2, 2, 2))
            self.assertEqual(h5['y'].shape, (2, 2, 2))

        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='stack',
                                        axis=-1,
                                        shape=(2, 2))
            self.assertEqual(h5['x'].shape, (2, 2, 2))
            self.assertEqual(h5['y'].shape, (2, 2, 2))

    def test_slicing(self):
        with h5tbx.File() as h5:
            ds_scale = h5.create_dataset('time', data=np.linspace(0, 1, 10),
                                         make_scale=True)
            ds = h5.create_dataset('grp/data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30),
                                   attach_scales=(ds_scale,))
            self.assertEqual(ds[0, :, :].shape, (20, 30))
            self.assertEqual(ds[:, 0, :].shape, (10, 30))
            self.assertEqual(ds[:, :, 0].shape, (10, 20))
            self.assertEqual(ds[1:4, 1:4, 1:4].shape, (3, 3, 3))
            self.assertEqual(ds[1:4, :, :].shape, (3, 20, 30))
            self.assertEqual(list(ds[1:4, :, :].coords.keys()), ['time'])
            self.assertEqual(list(ds[1:4, 1:4, :].coords.keys()), ['time', ])
            self.assertEqual(list(ds[1:4, 1:4, 1:4].coords.keys()), ['time', ])

            self.assertTrue(ds[..., 0].equals(ds[:, :, 0]))
            self.assertTrue(ds[0, ...].equals(ds[0, :, :]))
            self.assertTrue(ds[..., :].equals(ds[:, :, :]))
            self.assertTrue(ds[...].equals(ds[:, :, :]))

    def test_modify_static_properties(self):
        with h5tbx.File() as h5:
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

        with h5tbx.File() as h5:
            ds = h5.create_dataset('data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30))
            ds0 = ds[:]

            new_ds = ds.modify(chunks=(2, 5, 6))
            ds1 = new_ds[:]

            self.assertEqual(ds.chunks, (1, 20, 30))
            self.assertEqual(new_ds.chunks, (2, 5, 6))
        self.assertTrue(np.all(ds1 == ds0))

        with h5tbx.File() as h5:
            ds = h5.create_dataset('data', shape=(10, 20, 30),
                                   data=np.random.rand(10, 20, 30),
                                   chunks=(1, 20, 30),
                                   dtype=int)
            new_ds = h5['/'].modify_dataset_properties(dataset=ds,
                                                       dtype=float)
            with self.assertRaises(TypeError):
                h5['/'].modify_dataset_properties(ds, 4.3)
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

        with h5tbx.File() as h5:
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
        with h5tbx.File() as h5:
            h5.create_dataset('time', data=range(0, 100), make_scale=True)
            h5.create_dataset('x', data=range(0, 100), make_scale=True)
            h5.create_dataset('y', data=range(0, 200), make_scale=True)
            ds = h5.create_dataset('data', np.random.rand(100, 200, 100), attach_scale=('time', 'y', 'x'))

            self.assertEqual(ds[:, :, :].shape, (100, 200, 100))
            self.assertEqual(ds[0, :, :].shape, (200, 100))
            self.assertEqual(ds[:, 0, :].shape, (100, 100))
            self.assertEqual(ds[:, :, 0].shape, (100, 200))
            self.assertEqual(list(ds[:, :, :].coords.keys()), ['time', 'y', 'x'])
            self.assertEqual(list(ds[0, :, :].coords.keys()), ['time', 'y', 'x'])
            self.assertEqual(list(ds[:, 0, :].coords.keys()), ['time', 'y', 'x'])
            self.assertEqual(list(ds[:, :, 0].coords.keys()), ['time', 'y', 'x'])
            self.assertEqual(list(ds[:, 0, 0].coords.keys()), ['time', 'y', 'x'])

            np.testing.assert_equal(h5.data.time > 66, np.arange(67, 100))

            self.assertEqual(h5.data[h5.data.time > 66, :, :].shape, (33, 200, 100))
            np.testing.assert_equal(h5.data.time > 66, np.arange(67, 100, 1))
            np.testing.assert_equal(h5.data.time >= 66, np.arange(66, 100, 1))
            np.testing.assert_equal(h5.data.time < 66, np.arange(0, 66, 1))
            np.testing.assert_equal(h5.data.time <= 66, np.arange(0, 67, 1))
            self.assertEqual(h5.data[h5.data.time == 66, :, :].shape, (1, 200, 100))
            np.testing.assert_equal(h5.data[h5.data.time == 66, :, :], h5.data.values[66, :, :].reshape(1, 200, 100))
            np.testing.assert_equal(h5.data.time == 66, np.array(66))

    def test_Group(self):
        with h5tbx.File() as h5:
            grp = h5.create_group('grp')
            grp.create_dataset('data', data=np.random.rand(10, 20, 30))
            self.assertEqual(grp.get_datasets('data'), [grp['data'], ])
            self.assertEqual(grp.get_datasets('dat*'), [grp['data'], ])
            self.assertEqual(grp.get_datasets('idat*'), [])
            with self.assertRaises(ValueError):
                h5tbx.core.Group(4.3)
            with self.assertRaises(TypeError):
                h5.grp['New'] = (4.3, int)
            h5.grp['New'] = dict(data=np.random.rand(10, 20, 30))

            newds = h5.grp['New']
            self.assertEqual(newds.name, '/grp/New')

            from h5rdmtoolbox.wrapper.core import Lower
            newds = h5.grp[Lower('new')]
            self.assertEqual(newds.name, '/grp/New')

            self.assertEqual(str(h5.grp), '<HDF5 wrapper group "/grp" (members: 2, convention: "default")>')

            with self.assertRaises(ValueError):
                grp = h5.create_group('grp')
            self.assertTrue('a' not in grp.attrs)
            grp = h5.create_group('grp', attrs={'a': 'b'}, overwrite=True)
            self.assertTrue('a' in grp.attrs)

            h5.create_string_dataset('str', 'test')
            self.assertTrue('str' in h5)
            self.assertTrue(h5['str'].name, '/str')
            self.assertEqual(h5['str'][()], 'test')

            h5.create_string_dataset('str2', ('a', 'b', 'c'))
            self.assertTrue(h5['str2'].name, '/str2')
            self.assertEqual(h5['str2'][()], ('a', 'b', 'c'))

            h5.create_string_dataset('str2', ('a', 'bb', 'c', 'd'), overwrite=True)
            self.assertTrue(h5['str2'].name, '/str2')
            self.assertEqual(h5['str2'][()], ('a', 'bb', 'c', 'd'))
            self.assertTrue(h5['str2'].size, 2)

            h5.create_string_dataset('str2', ('a', 'b', 'c', 'dddd'), overwrite=True, attrs={'a': 'b'})
            self.assertTrue(h5['str2'].name, '/str2')
            self.assertEqual(h5['str2'][()], ('a', 'b', 'c', 'dddd'))
            self.assertTrue(h5['str2'].size, 4)
