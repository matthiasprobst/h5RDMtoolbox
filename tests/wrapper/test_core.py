import datetime
import h5py
import json
import numpy as np
import pandas as pd
import pathlib
import unittest
import xarray as xr
from datetime import datetime

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import __version__
from h5rdmtoolbox.wrapper import h5yaml
from h5rdmtoolbox.wrapper.h5attr import AttributeString

logger = h5tbx.logger
logger.setLevel('ERROR')
__this_dir__ = pathlib.Path(__file__).parent


class TestCore(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_logger(self):
        from h5rdmtoolbox.utils import ToolboxLogger
        self.assertIsInstance(logger, ToolboxLogger)

    def test_lower(self):
        self.assertEqual(h5tbx.Lower('Hello'), 'hello')
        self.assertIsInstance(h5tbx.lower('Hello'), h5tbx.Lower)

    def test_File(self):
        self.assertEqual(str(h5tbx.File), "<class 'h5rdmtoolbox.wrapper.core.File'>")
        with h5tbx.File() as h5:
            self.assertEqual(h5.__str__(), '<class "File" convention: "h5py">')

    def test_Files(self):
        with h5tbx.File() as h5:
            f1 = h5.hdf_filename
        with h5tbx.File() as h5:
            f2 = h5.hdf_filename
        with h5tbx.Files([f1, ]) as h5:
            self.assertIsInstance(h5[0], h5tbx.File)
            self.assertEqual(str(h5), "<Files (1 files)>")
        with h5tbx.Files([f1, f2]) as h5:
            self.assertEqual(str(h5), "<Files (2 files)>")
            self.assertIsInstance(h5[0], h5tbx.File)
            self.assertIsInstance(h5[1], h5tbx.File)
        with h5tbx.Files([f1, f2], file_instance=h5tbx.File) as h5:
            self.assertEqual(str(h5), "<Files (2 files)>")
            self.assertIsInstance(h5[0], h5tbx.File)
            self.assertIsInstance(h5[1], h5tbx.File)

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

    def test_del(self):
        with h5tbx.use('h5tbx'):
            with h5tbx.File() as h5:
                ds = h5.create_dataset('ds', data=np.arange(10), units='m/s', attrs={'comment': 'test'})

                with self.assertRaises(ValueError):
                    del ds.units

                with self.assertRaises(AttributeError):
                    with h5tbx.set_config(natural_naming=False):
                        del ds.ds

                del h5.ds
                self.assertTrue('ds' not in h5)

    def test_setattr(self):
        with h5tbx.File() as h5:
            with self.assertRaises(KeyError):
                h5.smth = 10
            h5._smth = 10
            self.assertEqual(10, h5._smth)

    def test_rootparent(self):
        with h5tbx.File() as h5:
            g = h5.create_group('g')
            self.assertEqual(h5, g.rootparent)
            self.assertEqual(h5, h5['g'].rootparent)
            self.assertEqual(h5, h5.rootparent)

            grp = h5.create_group('grp1/grp2/grp3')
            self.assertEqual(grp.rootparent, h5['/'])
            dset = grp.create_dataset('test', data=1)
            self.assertEqual(dset.rootparent, h5['/'])

    def test_basename(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds', data=np.arange(10))
            self.assertEqual(h5['ds'].basename, 'ds')
            h5.create_dataset('a/b/ds', data=np.arange(10))
            self.assertEqual(h5['a/b/ds'].basename, 'ds')
            self.assertEqual(h5['a'].basename, 'a')
            self.assertEqual(h5['a/b'].basename, 'b')

    def test_write_iso_timestamp(self):
        with h5tbx.File() as h5:
            now = datetime.now()
            h5.write_iso_timestamp('timestamp', dt=now)
            self.assertIsInstance(h5.attrs['timestamp'], str)
            self.assertEqual(h5.attrs['timestamp'], str(now.isoformat()))
            with self.assertRaises(TypeError):
                h5.write_iso_timestamp('timestamp', dt='now', overwrite=True)

    def test_create_datasets_from_csv(self):
        df = pd.DataFrame({'x': [1, 5, 10, 0], 'y': [-3, 20, 0, 11.5]})
        csv_filename1 = h5tbx.utils.generate_temporary_filename(suffix='.csv')
        df.to_csv(csv_filename1, index=None)

        with h5tbx.File() as h5:
            with self.assertRaises(ValueError):
                h5.create_datasets_from_csv(csv_filenames=csv_filename1, combine_opt='invlaid')
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

        with h5tbx.File() as h5:
            x, y = h5.create_dataset_from_csv(csv_filename=csv_filename1, shape=(2, 2), dimension=None)
            self.assertEqual(x.shape, (2, 2))
            self.assertEqual(y.shape, (2, 2))
            np.testing.assert_equal(x[:], df['x'].values.reshape((2, 2)))
            np.testing.assert_equal(y[:], df['y'].values.reshape((2, 2)))

        with h5tbx.File() as h5:
            x, y = h5.create_dataset_from_csv(csv_filename=csv_filename1, dimension='x')
            self.assertTrue(x.is_scale)
            self.assertFalse(y.is_scale)
            self.assertEqual(h5['x'], h5['y'].dims[0][0])

        csv_filename2 = h5tbx.utils.generate_temporary_filename(suffix='.csv')

        df2 = -1 * df
        df2.to_csv(csv_filename2, index=None)

        # test concatenate
        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='concatenate')
            self.assertEqual(h5['x'].shape, (8,))
            self.assertEqual(h5['y'].shape, (8,))

        # test stack
        with h5tbx.File() as h5:
            h5.create_datasets_from_csv(csv_filenames=(csv_filename1, csv_filename2),
                                        combine_opt='stack', axis=0)
            self.assertEqual(h5['x'].shape, (2, 4))
            np.testing.assert_equal(df['x'].values, h5['x'].values[0, :])
            np.testing.assert_equal(df2['x'].values, h5['x'].values[1, :])
            np.testing.assert_equal(df['y'].values, h5['y'].values[0, :])
            np.testing.assert_equal(df2['y'].values, h5['y'].values[1, :])

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
                                         make_scale=True, overwrite=True)
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

    def test_ds_grp_name_existence(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset('ds', shape=(10, 20, 30))
            with self.assertRaises(ValueError):
                h5['/'].create_group('ds')

            with self.assertRaises(ValueError):
                h5['/'].create_group('name')

    def test_coord_selection(self):
        with h5tbx.File() as h5:
            x = h5.create_dataset('x', data=np.linspace(0, 1, 10), make_scale=True)
            y = h5.create_dataset('y', data=np.linspace(0, 1, 20), make_scale=True)
            time = h5.create_dataset('time', data=np.linspace(0, 1, 30), make_scale=True)
            ds = h5.create_dataset('data', shape=(10, 20, 30), attach_scales=(x, y, time))

    def test_modify_static_properties(self):
        with h5tbx.File() as h5:
            ds_scale = h5.create_dataset('time',
                                         data=np.linspace(0, 1, 10),
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
                                                       dtype=float,
                                                       tqdm_pbar=True)
            with self.assertRaises(TypeError):
                h5['/'].modify_dataset_properties(ds, 4.3)
            with self.assertRaises(KeyError):
                h5['/'].modify_dataset_properties(ds, dataset_properties=4.3)
            with self.assertRaises(KeyError):
                h5['/'].modify_dataset_properties(ds, dataset_properties=dict(a=4.3))

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
            self.assertEqual(sorted(grp.get_datasets('.*')), [grp['data'], ])
            self.assertEqual(grp.get_datasets('idat*'), [])
            with self.assertRaises(ValueError):
                h5tbx.Group(4.3)
            with self.assertRaises(TypeError):
                h5.grp['New'] = (4.3, int)
            h5.grp['New'] = dict(data=np.random.rand(10, 20, 30))

            newds = h5.grp['New']
            self.assertEqual(newds.name, '/grp/New')

            from h5rdmtoolbox.wrapper.core import Lower
            newds = h5.grp[Lower('new')]
            self.assertEqual(newds.name, '/grp/New')

            self.assertEqual(str(h5.grp), '<HDF5 wrapper group "/grp" (members: 2, convention: "h5py")>')

            h5.grp['ds_from_xr_data_array'] = xr.DataArray(np.random.rand(10, 20, 30))
            self.assertTrue('ds_from_xr_data_array' in h5.grp)
            self.assertEqual((10, 20, 30), h5.grp['ds_from_xr_data_array'].shape)

            h5.grp['ds_from_list'] = np.array([1, 2, 3]), dict(attrs=dict(a=1))
            self.assertTrue('ds_from_list' in h5.grp)
            self.assertEqual((3,), h5.grp['ds_from_list'].shape)

            with self.assertRaises(ValueError):
                grp = h5.create_group('grp')
            self.assertTrue('a' not in grp.attrs)
            grp = h5.create_group('grp', attrs={'a': 'b'}, overwrite=True)
            self.assertTrue('a' in grp.attrs)

            with self.assertRaises(TypeError):
                h5.create_string_dataset('str', np.array([1, 2, 3]))

            h5.create_string_dataset('str', 'test', attrs={'a': 'b'})
            self.assertTrue('str' in h5)
            self.assertEqual(h5['str'].attrs['a'], 'b')
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

            self.assertEqual('/grp', h5['grp'].name)

    # ---------------------------------------------------------------------------
    # special dataset creation methods:
    # ---------------------------------------------------------------------------
    def test_create_img_dataset(self):

        # Iterable class:
        class ImgReader:
            def __init__(self, imgdir):
                self._imgdir = imgdir
                self._index = 0
                self._size = 5

            def read_img(self):
                return np.random.random((20, 10))

            def __iter__(self):
                return self

            def __len__(self):
                return self._size

            def __next__(self):
                if self._index < self._size:
                    self._index += 1
                    return self.read_img()
                raise StopIteration

        imgreader = ImgReader('testdir')
        with h5tbx.File() as h5:
            ds = h5.create_dataset_from_image(imgreader, 'testimg', axis=0)
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))
            # reset imgreader
            imgreader._index = 0
            ds = h5.create_dataset_from_image(imgreader, 'testimg2', axis=-1)
            self.assertEqual(ds.shape, (20, 10, 5))
            self.assertEqual(ds.chunks, (20, 10, 1))

        # write more tests for create_dataset_from_image:
        with h5tbx.File() as h5:
            ds = h5.create_dataset_from_image([np.random.random((20, 10))] * 5,
                                              'testimg', axis=0)
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))

        imgreader._index = 0
        h5tbx.use('h5py')
        with h5tbx.File() as h5:
            ds = h5.create_dataset_from_image(imgreader, 'testimg', axis=0,
                                              attrs=dict(units='', long_name='test'))
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))
            # reset imgreader
            imgreader._index = 0
            ds = h5.create_dataset_from_image(imgreader, 'testimg2', axis=-1,
                                              attrs=dict(units='', long_name='test'))
            self.assertEqual(ds.shape, (20, 10, 5))
            self.assertEqual(ds.chunks, (20, 10, 1))

        # write more tests for create_dataset_from_image:
        with h5tbx.File() as h5:
            ds = h5.create_dataset_from_image([np.random.random((20, 10))] * 5,
                                              'testimg', axis=0, attrs=dict(units='', long_name='test'))
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))

    def test_properties(self):
        with h5tbx.File() as h5:
            self.assertIsInstance(h5.creation_time, datetime)
            now = datetime.now().astimezone()
            file_now = h5.creation_time
            self.assertTrue(abs((file_now - now).total_seconds()) < 1)
            self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
            self.assertEqual(h5.version, __version__)
            self.assertEqual(h5.filesize.units, h5tbx.get_ureg().byte)
            self.assertIsInstance(h5.hdf_filename, pathlib.Path)

    def test_special_attribute_types(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=np.random.random((10, 10)))
            grp = h5.create_group('grp')
            for obj in (h5, ds, grp):
                self.assertTrue(isinstance(obj.attrs, h5tbx.wrapper.h5attr.WrapperAttributeManager))

                obj.attrs['a_tuple'] = (1, 2, 'awd', {'k': 'v', 'k2': 2})
                t = obj.attrs['a_tuple']
                self.assertIsInstance(t, tuple)
                self.assertEqual(t, (1, 2, 'awd', {'k': 'v', 'k2': 2}))

                obj.attrs['a_list'] = [1, 2, 'awd', {'k': 'v', 'k2': 2}]
                t = obj.attrs['a_list']
                self.assertIsInstance(t, list)
                self.assertEqual(t, [1, 2, 'awd', {'k': 'v', 'k2': 2}])
                obj.attrs.rename('a_list', 'a_new_list')
                t = obj.attrs['a_new_list']
                self.assertIsInstance(t, list)
                self.assertEqual(t, [1, 2, 'awd', {'k': 'v', 'k2': 2}])

                obj.attrs['an_attr'] = 'a_string'
                self.assertEqual(obj.attrs['an_attr'], 'a_string')
                obj.attrs['mean'] = 1.2
                self.assertEqual(obj.attrs['mean'], 1.2)

                # testing links:
                obj.attrs['link_to_group'] = h5['/']
                self.assertEqual(obj.attrs['link_to_group'], '/')
                self.assertIsInstance(obj.attrs['link_to_group'], str)
                obj.attrs['link_to_ds'] = ds
                self.assertEqual(obj.attrs['link_to_ds'], ds.name)
                self.assertIsInstance(obj.attrs['link_to_ds'], str)
                obj.attrs['attribute_of_links_to_ds'] = {'ds': ds, 'grp': grp, 'astr': 'test', 'afloat': 3.1}
                self.assertIsInstance(obj.attrs['attribute_of_links_to_ds'], dict)
                self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['ds'], h5py.Dataset)
                self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['grp'], h5py.Group)
                self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['astr'], str)
                self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['afloat'], float)

                # testing units
                test_vals = ('1.2m', '1.2 m', '1.2 [m]', '1.2 (m)')
                for test_val in test_vals:
                    obj.attrs['mean_with_unit'] = test_val
                    self.assertEqual(obj.attrs['mean_with_unit'], test_val)
                    attrs_with_unit = obj.attrs['mean_with_unit'].to_pint()
                    self.assertEqual(f"{obj.attrs['mean_with_unit'].to_pint()}", '1.2 m')
                    self.assertEqual(h5tbx.get_config('ureg_format'), 'C~')
                    self.assertEqual(h5tbx.get_ureg().default_format, 'C~')
                    self.assertEqual(h5tbx.get_ureg().default_format, h5tbx.get_config('ureg_format'))
                    self.assertEqual(f"{obj.attrs['mean_with_unit'].to_pint()}", '1.2 m')
                    self.assertEqual(attrs_with_unit, h5tbx.get_ureg()(test_val))
                    obj.attrs['mean_with_unit'] = attrs_with_unit
                    self.assertEqual(obj.attrs['mean_with_unit'], str(h5tbx.get_ureg()(test_val)))

                self.assertEqual(obj.attrs.get('non_existing_attribute'), None)

    def test_create_from_yaml(self):

        h5y = h5yaml.H5Yaml(__this_dir__ / '../data/from_yaml.yaml')
        with h5tbx.File() as h5:
            h5y.write(h5)
            self.assertIn('grp', h5)
            self.assertIn('grp/supgrp', h5)
            self.assertIn('velocity', h5['grp/supgrp'])
            self.assertEqual('Title of the file', h5.attrs['title'])
            self.assertEqual('0000-1234-1234-1234', h5.attrs['contact'])

        with h5tbx.File() as h5:
            h5.create_from_yaml(__this_dir__ / '../data/from_yaml.yaml')
            self.assertIn('grp', h5)
            self.assertIn('grp/supgrp', h5)
            self.assertIn('velocity', h5['grp/supgrp'])
            self.assertEqual('Title of the file', h5.attrs['title'])
            self.assertEqual('0000-1234-1234-1234', h5.attrs['contact'])
            h5.dumps()

    def test_flag(self):
        with h5tbx.File() as h5:
            time = h5.create_dataset('time', data=[1, 2, 3], make_scale=True)
            ds = h5.create_dataset('ds', data=[5, 10, 0], attach_scales='time')
            # with self.assertRaises(KeyError):
            #     self.assertEqual(ds[0:2].flag.where(1, 0).shape, (2,))
            flag = h5.create_dataset('flag', data=[1, 0, 0], attach_scales='time')
            ds.attach_ancillary_dataset(flag)
            data = ds[:]

        self.assertEqual(data[0:2].flag.where(1, 0).shape, (2,))

    def test_create_dataset_from_xr(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds', data=xr.DataArray([1, 2, 3], dims=['time'], coords={'time': [1, 2, 3]}),
                              compression='gzip', compression_opts=1)
            self.assertEqual(1, h5['ds'].compression_opts)
            h5.create_dataset('ds0', data=xr.DataArray(0),
                              compression='gzip', compression_opts=1)  # will be ignored
            self.assertEqual(0, h5['ds0'].ndim)

            h5.create_dataset('ds_similar', data=xr.DataArray([1, 2, 3], dims=['time'], coords={'time': [1, 2, 3]}),
                              compression='gzip', compression_opts=2)
            self.assertEqual(2, h5['ds_similar'].compression_opts)

            h5.create_dataset('ds_coordinate', data=xr.DataArray([1, 2, 3], dims=['ds0'], coords={'z': 0}))
            self.assertEqual('z', h5['ds_coordinate'].attrs['COORDINATES'][0])

            with self.assertRaises(ValueError):
                h5.create_dataset('ds', data=xr.DataArray([1, 2, 3], dims=['time'], coords={'time': [1, 4, 3]}))
            self.assertEqual(h5['ds'],
                             h5.create_dataset('ds',
                                               data=xr.DataArray([1, 2, 3], dims=['time'], coords={'time': [1, 2, 3]}),
                                               overwrite=False))
            h5.create_dataset('ds', data=xr.DataArray([1, 2, 30], dims=['time'], coords={'time': [1, 2, 3]}),
                              overwrite=True, dtype='int64')
            self.assertEqual((3,), h5['ds'].shape)
            self.assertEqual('int64', h5['ds'].dtype)
            self.assertEqual('time', h5['ds'][()].dims[0])
            np.testing.assert_equal(np.array([1, 2, 3]), h5['time'][()].values)
            np.testing.assert_equal(np.array([1, 2, 3]), h5['time'].values[()])
            np.testing.assert_equal(np.array([1, 2, 30]), h5['ds'][()].values)
            np.testing.assert_equal(np.array([1, 2, 30]), h5['ds'].values[()])

            with self.assertRaises(ValueError):
                h5.create_dataset('name', data=1)

            h5.create_dataset('ds2', data=xr.DataArray([10, 2, 3], dims=['time'], coords={'time': [1, 2, 3]},
                                                       attrs={'units': 'm'}),
                              dtype='int64')
            self.assertEqual((3,), h5['ds2'].shape)
            self.assertEqual('int64', h5['ds2'].dtype)
            self.assertEqual('time', h5['ds2'][()].dims[0])
            np.testing.assert_equal(np.array([1, 2, 3]), h5['time'][()].values)
            np.testing.assert_equal(np.array([1, 2, 3]), h5['time'].values[()])
            np.testing.assert_equal(np.array([10, 2, 3]), h5['ds2'][()].values)
            np.testing.assert_equal(np.array([10, 2, 3]), h5['ds2'].values[()])
            self.assertEqual('m', h5['ds2'].attrs['units'])

    def test_create_dataset_scale_issues(self):
        with h5tbx.File() as h5:
            with self.assertRaises(ValueError):
                h5.create_dataset('flag', data=[1, 0, 1], dtype='int8', make_scale=True, attach_scale='time')

    def test_coords(self):
        with h5tbx.File() as h5:
            h5.create_dataset('time', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('vel', data=[1.5, 2.5, 3.5], attach_scales='time')
            h5.create_dataset('vel_no_scale', data=[1.5, 2.5, 3.5])
            self.assertIsInstance(h5['vel'].coords(), dict)
            self.assertEqual('time', list(h5['vel'].coords().keys())[0])
            self.assertEqual({'time': h5['time']}, h5['vel'].coords())
            self.assertEqual({}, h5['vel_no_scale'].coords())

    def test_isel_sel(self):
        with h5tbx.File() as h5:
            h5.create_dataset('time', data=[1, 2, 3], make_scale=True)
            h5.create_dataset('vel', data=[1.5, 2.5, 3.5], attach_scales='time')
            np.testing.assert_equal(h5['vel'].values[0:2], h5['vel'].isel(time=slice(0, 2)).values)
            self.assertEqual(3.5, float(h5['vel'].isel(time=2)))
            with self.assertRaises(KeyError):
                h5['vel'].isel(x=2)
            self.assertEqual(2.5, float(h5['vel'].sel(time=2)))
            self.assertEqual(2.5, float(h5['vel'].sel(time=2.0)))
            with self.assertRaises(ValueError):
                h5['vel'].sel(time=1.2)
            with self.assertRaises(NotImplementedError):
                h5['vel'].sel(time=1.2, method='invalid')
            self.assertEqual(1.5, float(h5['vel'].sel(time=1.2, method='nearest')))

    def test_create_dataset_with_ancillary_ds(self):
        with h5tbx.File() as h5:
            h5.create_dataset('flag', data=[1, 0, 1], dtype='int8')
            self.assertEqual(h5['flag'].dtype, np.dtype('int8'))
            h5.create_dataset('flag2', data=[0, 0], dtype='int8', make_scale='the_flag_2')

            with self.assertRaises(TypeError):
                h5.create_dataset(name='vel', data=[1.5, 2.5, 3.5], ancillary_datasets={'flag': 'flag', })
            with self.assertRaises(ValueError):
                h5.create_dataset(name='vel', data=[1.5, 2.5, 3.5], ancillary_datasets={'flag': h5['flag2'], })
            h5.create_dataset(name='vel', data=[1.5, 2.5, 3.5], ancillary_datasets={'flag': h5['flag'], })
            self.assertIsInstance(h5['vel'].ancillary_datasets, dict)
            self.assertEqual(h5['vel'].ancillary_datasets['flag'], h5['flag'])
            h5['vel'].attrs['ancillary_datasets'] = json.dumps({'flag2': 'flag2'})
            self.assertIsInstance(h5['vel'].ancillary_datasets, dict)
            self.assertEqual(h5['vel'].ancillary_datasets['flag'], h5['flag'])

            h5['vel'].attach_ancillary_dataset(h5['flag'])
            self.assertIsInstance(h5['vel'].ancillary_datasets, dict)
            self.assertEqual(h5['vel'].ancillary_datasets['flag'], h5['flag'])
            with self.assertRaises(ValueError):
                h5['vel'].attach_ancillary_dataset(h5['flag2'])

            with self.assertRaises(ValueError):
                # wrong shape
                h5.create_dataset(name='vel2', data=[1.5, 2.5, 4.5], attach_scale='flag2')
            h5.create_dataset(name='vel2', data=[1.5, 2.5], attach_scale='flag2')
            self.assertEqual(['the_flag_2'], list(h5['vel2'].dims[0].keys()))

            h5.create_dataset(name='3D', data=np.random.rand(2, 3, 4), make_scale=True)
            with self.assertRaises(ValueError):
                h5.create_dataset('vel3', data=[1.5, 2.5], attach_scale='3D')
