import datetime
import logging
import unittest
from pathlib import Path

import h5py
import numpy as np
import xarray
import xarray as xr
import yaml
from pint_xarray import unit_registry as ureg

from h5rdmtoolbox import h5wrapper, __version__
from h5rdmtoolbox.conventions.data import DataSourceType
from h5rdmtoolbox.conventions.standard_names import StandardNameConvention, StandardNameError
from h5rdmtoolbox.h5wrapper import H5File
from h5rdmtoolbox.h5wrapper import config
from h5rdmtoolbox.h5wrapper import set_loglevel
from h5rdmtoolbox.h5wrapper.h5base import WrapperAttributeManager
from h5rdmtoolbox.h5wrapper.h5file import H5Dataset
from h5rdmtoolbox.h5wrapper.h5file import H5Group
from h5rdmtoolbox.utils import generate_temporary_filename, touch_tmp_hdf5_file

logger = logging.getLogger('h5rdmtoolbox.h5wrapper')
set_loglevel('error')


class TestH5File(unittest.TestCase):

    def test_empty_convention(self):
        self.assertTrue(H5File.Layout.filename.exists())
        self.assertEqual(H5File.Layout.filename.stem, 'H5File')
        with H5File() as h5:
            self.assertIsInstance(h5.sn_convention, StandardNameConvention)
            self.assertEqual(h5.sn_convention.version, 0)
            self.assertEqual(h5.sn_convention.name, 'EmptyStandardNameConvention')

    def test_create_dataset(self):
        """H5File has more parameters to pass as H5Base"""
        with H5File() as h5:
            with self.assertRaises(RuntimeError):
                _ = h5.create_dataset('u', shape=())
        with H5File() as h5:
            ds = h5.create_dataset('u', shape=(), long_name='velocity')
            self.assertEqual(ds.name, '/u')
            self.assertEqual(ds.attrs['units'], '')
            self.assertEqual(ds.attrs['long_name'], 'velocity')
        with H5File() as h5:
            ds = h5.create_dataset('velocity', shape=(), standard_name='x_velocity')
            self.assertEqual(ds.attrs['units'], '')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
        with H5File() as h5:
            ds = h5.create_dataset('velocity', shape=(),
                                   standard_name='x_velocity',
                                   units='m/s')
            self.assertEqual(ds.attrs['units'], 'm/s')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
        da = xr.DataArray(data=[1, 2, 3], attrs={'units': 'm/s'})
        with H5File() as h5:
            with self.assertRaises(RuntimeError):
                _ = h5.create_dataset('velocity', data=da)

        da = xr.DataArray(data=[1, 2, 3], attrs={'units': 'm/s', 'standard_name': 'x_velocity'})
        with H5File() as h5:
            ds = h5.create_dataset('velocity', data=da)
            self.assertEqual(ds.attrs['units'], 'm/s')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_create_group(self):
        """testing the creation of groups"""
        with H5File() as h5:
            grp = h5.create_group('testgrp2', long_name='a long name')
            self.assertEqual(grp.attrs['long_name'], 'a long name')
            self.assertEqual(grp.long_name, 'a long name')

    def test_Layout(self):
        self.assertTrue(H5File.Layout.filename.exists())
        self.assertEqual(H5File.Layout.filename.stem, 'H5File')
        with H5File() as h5:
            h5.create_dataset('test', shape=(3,), long_name='daadw')
            h5.create_dataset('testgrp/ds2', shape=(30,), long_name='daadw')
            n_issuess = h5.check()

    def test_attrs(self):
        with H5File(mode='w') as h5:
            h5.attrs['mean'] = 1.2
            self.assertTrue(isinstance(h5.attrs, WrapperAttributeManager))

            config.natural_naming = False

            with self.assertRaises(AttributeError):
                self.assertEqual(h5.attrs.mean, 1.2)

            config.natural_naming = True

            self.assertEqual(h5.attrs.mean, 1.2)
            h5.attrs.title = 'title of file'
            self.assertEqual(h5.attrs['title'], 'title of file')

            h5.attrs['gr'] = h5['/']
            self.assertEqual(h5.attrs['gr'].name, '/')

            h5.attrs.gr2 = h5['/']
            self.assertEqual(h5.attrs['gr2'].name, '/')

            dset = h5.create_dataset('ds', data=1, long_name='a long name', attrs={'a1': 1, 'a2': 'str',
                                                                                   'a3': {'a': 2}})
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            h5.attrs['ds'] = dset
            self.assertEqual(h5.attrs['ds'], dset)
            self.assertIsInstance(h5.attrs['ds'], H5Dataset)

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

    def test_H5File_and_standard_name(self):
        with self.assertRaises(FileExistsError):
            with H5File(mode='w', sn_convention='wrong file name'):
                pass
        with H5File(mode='w', sn_convention=None) as h5:
            self.assertIsInstance(h5.sn_convention, StandardNameConvention)

    def test_creation_time(self):
        with H5File(mode='w') as h5:
            self.assertIsInstance(h5.creation_time, datetime.datetime)

    def test_data_source_type(self):
        with H5File(mode='w') as h5:
            self.assertIsInstance(h5.data_source_type, DataSourceType)
            self.assertEqual(h5.data_source_type, DataSourceType.none)
            h5.attrs['data_source_type'] = 'experimental'
            self.assertEqual(h5.data_source_type, DataSourceType.experimental)

    def test_title(self):
        with H5File(mode='w') as h5:
            self.assertEqual(h5.title, None)
            h5.title = 'my title'
            self.assertEqual(h5.title, 'my title')

    def test_version(self):
        with H5File(mode='w') as h5:
            self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
            self.assertEqual(h5.version, __version__)

    def test_filesize(self):
        with H5File(mode='w') as h5:
            self.assertEqual(h5.filesize.units, ureg.byte)

    def test_moveto(self):
        with H5File(mode='w') as h5:
            new_filename = h5.moveto('.')
            self.assertTrue(new_filename.exists())
        new_filename.unlink()

    def test_saveas(self):
        with H5File(mode='w') as h5:
            new_filename = h5.saveas('here.hdf')
            self.assertTrue(new_filename.exists())
        new_filename.unlink()

    def test_open(self):
        with H5File(mode='w') as h5:
            pass
        h5.open('r+')
        self.assertEqual(h5.mode, 'r+')
        h5.close()

    def test_create_group(self):
        with H5File() as h5:
            grp = h5.create_group('test_grp')
            self.assertIsInstance(grp, H5Group)
            grp = grp.create_group('test_grp')
            self.assertIsInstance(grp, H5Group)

    def test_groups(self):
        with H5File() as h5:
            groups = h5.groups
            self.assertEqual(groups, [])


class TestH5Dataset(unittest.TestCase):
    """
    Test functions to test every method/functionality/feature available through H5Dataset
    """

    def tearDown(self) -> None:
        for fname in Path(__file__).parent.glob('*'):
            if fname.suffix not in ('py', '.py', ''):
                fname.unlink()

    def test_rootparent(self):
        with H5File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertIsInstance(grp, H5Group)
            dset = grp.create_dataset('test', data=1, long_name='some long name')
            self.assertIsInstance(dset, H5Dataset)
            self.assertEqual(dset.rootparent, h5['/'])

    def test_rename(self):
        with H5File(mode='w') as h5:
            h5.create_dataset('testds', units='', long_name='random', data=np.random.rand(10, 10))
            h5.testds.rename('newname')
            ds = h5.create_dataset('testds_scale', units='', long_name='random long name', data=np.random.rand(10, 10))
            ds.make_scale()
            with self.assertRaises(RuntimeError):
                ds.rename('newname2')

    def test_to_unit(self):
        with H5File(mode='w') as h5:
            dset = h5.create_dataset('temp', units='degC', long_name='temperature dataset', data=20)
            self.assertEqual(dset.units, 'degC')
            self.assertEqual(float(dset[()].values), 20)
            dset.to_units('K')
            self.assertEqual(dset.units, 'K')
            self.assertEqual(float(dset[()].values), 293)

            dset = h5.create_dataset('temp2', units='degC',
                                     long_name='temperature dataset', data=[20, 30])
            self.assertEqual(dset.units, 'degC')
            self.assertEqual(float(dset[()].values[0]), 20)
            self.assertEqual(float(dset[()].values[1]), 30)
            dset.to_units('K')
            self.assertEqual(dset.units, 'K')
            self.assertEqual(float(dset[()].values[0]), 293)
            self.assertEqual(float(dset[()].values[1]), 303)

    def test_scale_manipulation(self):
        with H5File(mode='w') as h5:
            h5.create_dataset('x', long_name='x-coordinate', units='m', data=np.random.rand(10))
            h5.create_dataset('time', long_name='time', units='s', data=np.random.rand(10))
            h5.create_dataset('temp', long_name='temperature', units='K', data=np.random.rand(10),
                              attach_scale=((h5['x'], h5['time']),))
            self.assertTrue(h5['temp'].dims[0])
            h5['temp'].set_primary_scale(0, 1)

    def test_sdump(self):
        with H5File(mode='w') as h5:
            h5.attrs['creation_time'] = '2022-07-19T17:01:41Z+0200'
            h5.attrs['modification_time'] = '2022-07-19T17:01:41Z+0200'
            sdump_str = h5.sdump(ret=True)
            _str = """> H5File: Group name: /.
\x1B[3m
a: __h5rdmtoolbox_version__:      0.1.0\x1B[0m\x1B[3m
a: __wrcls__:                     H5File\x1B[0m\x1B[3m
a: creation_time:                 2022-07-19T17:01:41Z+0200\x1B[0m\x1B[3m
a: modification_time:             2022-07-19T17:01:41Z+0200\x1B[0m
"""
            self.assertEqual(sdump_str, _str)
        with H5File(mode='w') as h5:
            h5.attrs['creation_time'] = '2022-07-19T17:01:41Z+0200'
            h5.attrs['modification_time'] = '2022-07-19T17:01:41Z+0200'
            h5.create_dataset('test', shape=(), long_name='a long name')
            grp = h5.create_group('grp')
            grp.create_dataset('test', shape=(), long_name='a long name')
            sdump_str = h5.sdump(ret=True)
            _str = """> H5File: Group name: /.
\x1B[3m
a: __h5rdmtoolbox_version__:      0.1.0\x1B[0m\x1B[3m
a: __wrcls__:                     H5File\x1B[0m\x1B[3m
a: creation_time:                 2022-07-19T17:01:41Z+0200\x1B[0m\x1B[3m
a: modification_time:             2022-07-19T17:01:41Z+0200\x1B[0m
\x1B[1mtest\x1B[0m                   ()                            
\x1B[3m\x1B[1m/grp\x1B[0m\x1B[0m
  \x1B[1mtest\x1B[0m                   ()                            
"""
            self.assertEqual(sdump_str, _str)


class TestH5Group(unittest.TestCase):

    def tearDown(self) -> None:
        for fname in Path(__file__).parent.glob('*'):
            if fname.suffix not in ('py', '.py', ''):
                fname.unlink()

    def test_attrs(self):
        with H5File(mode='w') as h5:
            h5.attrs['mean'] = 1.2
            self.assertTrue(isinstance(h5.attrs, WrapperAttributeManager))

            config.natural_naming = False

            with self.assertRaises(AttributeError):
                self.assertEqual(h5.attrs.mean, 1.2)

            config.natural_naming = True

            self.assertEqual(h5.attrs.mean, 1.2)
            h5.attrs.title = 'title of file'
            self.assertEqual(h5.attrs['title'], 'title of file')

            h5.attrs['gr'] = h5['/']
            self.assertEqual(h5.attrs['gr'].name, '/')

            h5.attrs.gr2 = h5['/']
            self.assertEqual(h5.attrs['gr2'].name, '/')

            dset = h5.create_dataset('ds', data=1, long_name='a long name', attrs={'a1': 1, 'a2': 'str',
                                                                                   'a3': {'a': 2}})
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            h5.attrs['ds'] = dset
            self.assertEqual(h5.attrs['ds'], dset)
            self.assertIsInstance(h5.attrs['ds'], H5Dataset)

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

    def test_units(self):
        with H5File(mode='w', title='semantic test file') as h5:
            ds = h5.create_dataset(name='x', standard_name='x_coordinate', shape=(10, 20))
            self.assertEqual(ds.units, '')
            ds.units = 'm'
            self.assertEqual(ds.units, 'm')
            # with self.assertRaises(WrongStandardNameUnit):
            ds.units = 'kg'
            # cannot check units although obviously wrong, because it is not listed in convention
            h5.create_dataset(name='y', units='m/s',
                              standard_name='y_coordinate', shape=(10, 20))
            # with self.assertRaises(WrongStandardNameUnit):
            h5.create_dataset(name='u', units='m/kg',
                              standard_name='x_velocity', shape=(10, 20))

    def test_rootparent(self):
        with H5File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertEqual(grp.rootparent, h5['/'])

    def test_create_group(self):
        with H5File(mode='w') as h5:
            grp = h5.create_group('group')
            self.assertEqual(h5.long_name, None)
            grp.long_name = 'long name of group'
            self.assertEqual(grp.long_name, 'long name of group')

    def test_create_dataset(self):
        config.natural_naming = True
        sc = StandardNameConvention(standard_name_dict={}, name='Test_SNC', version=1,
                                    contact='contact@python.com', institution='my_institution')
        sc.set('time', canonical_units='s', description='physical time')
        sc.set('x_velocity', canonical_units='m/s',
               description='velocity is a vector quantity. x indicates the component in x-axis direction')
        sc.set('y_velocity', canonical_units='m/s',
               description='velocity is a vector quantity. y indicates the component in y-axis direction')
        sc.set('z_velocity', canonical_units='m/s',
               description='velocity is a vector quantity. z indicates the component in z-axis direction')

        with H5File(mode='w', sn_convention=sc) as h5:
            with self.assertRaises(RuntimeError):
                ds = h5.create_dataset('ds', shape=(2, 3))
            with self.assertRaises(StandardNameError):
                ds = h5.create_dataset('vel', shape=(2, 3), standard_name='x_velocity')
            with self.assertRaises(StandardNameError):
                ds = h5.create_dataset('vel', shape=(2, 3), standard_name='x_velocity_wrong')
            ds = h5.create_dataset('vel', shape=(2, 3), standard_name='x_velocity', units='m/s')
            self.assertEqual(ds.units, 'm/s')

            ds[:] = np.random.rand(2, 3)
            self.assertTrue(isinstance(ds[:], xarray.DataArray))
            self.assertTrue(isinstance(ds.values[:], np.ndarray))
            h5.create_dataset('grp/test', shape=(1,),
                              long_name='a long name')
            self.assertIn('test', h5['grp'])

            dset = h5.create_dataset('default_compression', data=[1, 2, 3], long_name='default long_name of dset')
            self.assertEqual(dset.compression, config.hdf_compression)
            self.assertEqual(dset.compression_opts, config.hdf_compression_opts)
            config.hdf_compression = 'gzip'
            config.hdf_compression_opts = 2
            dset = h5.create_dataset('other_compression', data=[1, 2, 3], long_name='default long_name of dset')
            self.assertEqual(dset.compression, 'gzip')
            self.assertEqual(dset.compression_opts, 2)

    def test_assign_data_to_existing_dset(self):
        config.natural_naming = True
        with H5File(mode='w') as h5:
            ds = h5.create_dataset('ds', shape=(2, 3), long_name='a long name')
            ds[0, 0] = 5
            self.assertEqual(ds[0, 0], 5)

    def test_create_dataset_from_xarray(self):
        config.natural_naming = True
        with H5File(mode='w') as h5:
            z = xarray.DataArray(name='z', data=-1,
                                 attrs=dict(units='m', standard_name='z_coordinate'))
            x = xarray.DataArray(name='x', data=[1, 2, 3], dims='x',
                                 attrs=dict(units='m', standard_name='x_coordinate'))
            u = xarray.DataArray(name='u', data=[1, 1, 1], coords={'x': x, 'z': z}, dims=('x',),
                                 attrs={'units': 'm/s', 'long_name': 'x-velocity'})

            h5.create_dataset('u', data=u)
            u = h5.u[:]
            self.assertTrue('COORDINATES' not in u.attrs)
            self.assertTrue('COORDINATES' in h5['u'].attrs)

            time = xarray.DataArray(dims='time', data=np.linspace(0, 1, 5),
                                    attrs={'standard_name': 'time'})
            h5['xr_data'] = xarray.DataArray(dims='time',
                                             data=np.random.rand(5, ),
                                             coords={'time': time},
                                             attrs={'long_name': 'xr data'})
            self.assertEqual(h5['xr_data'].shape, (5,))
            self.assertIn('time', h5)
            self.assertEqual(h5.xr_data.dims[0][0], h5['time'])

            with self.assertRaises(ValueError):
                h5['xr_data2'] = xarray.DataArray(dims='time',
                                                  data=np.random.rand(5, ),
                                                  coords={'time': np.linspace(0, 2, 5)})
            h5['xr_data2'] = xarray.DataArray(dims='time',
                                              data=np.random.rand(5, ),
                                              coords={'time': time},
                                              attrs={'long_name': 'xr data with same time coord'})
            self.assertIn('long_name', h5['xr_data2'].attrs)

            xrtime2 = xarray.DataArray(dims='time2', data=np.linspace(0, 3, 5), attrs={'standard_name': 'time'})
            ds = h5.create_dataset('xr_data3', data=xarray.DataArray(dims='time2',
                                                                     data=np.random.rand(5, ),
                                                                     coords={'time2': xrtime2},
                                                                     attrs={'standard_name': 'time'}))
            with self.assertRaises(ValueError):
                # dataset "time" already exists
                h5.create_dataset('xr_data4', data=xarray.DataArray(dims='time',
                                                                    data=np.random.rand(5, ),
                                                                    coords={'time': xrtime2}))

    def test_from_yaml_to_hdf(self):
        dictionary = {
            'datasets': {'boundary/outlet boundary/y': {'data': 2, 'units': 'm', 'standard_name': 'y_coordinate',
                                                        'attrs': {'comment': 'test', 'another_attr': 100.2,
                                                                  'array': [1, 2, 3]}}},
            'groups': {'test/grp': {'long_name': 'a test group'}}
        }
        yaml_file = generate_temporary_filename(suffix='.yaml')
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(dictionary, f)

        hdf_filename = generate_temporary_filename(suffix='.hdf')
        with H5File(hdf_filename, 'w') as h5:
            h5.from_yaml(yaml_file)
            self.assertIn('test/grp', h5)
            self.assertIn('boundary/outlet boundary/y', h5)
            self.assertTrue(h5['boundary/outlet boundary/y'].units, 'm')

    def test_get_by_attribute(self):
        with H5File(mode='w') as h5:
            l = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(l, [])

            h5.create_dataset('test', data=2, units='m',
                              long_name='a long name')
            l = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(l, ['test'])
            h5.create_dataset('grp/test', data=2, units='m',
                              long_name='a long name 2')
            l = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(l, ['grp/test', 'test'])
            l = h5.get_datasets_by_attribute('long_name',
                                             'a long name')
            self.assertEqual(l, ['test', ])

            h5['grp'].long_name = 'grp1'
            r = h5.get_groups_by_attribute('long_name')
            self.assertEqual(r, ['grp'])

    def test_get_group_names(self):
        with H5File(mode='w') as h5:
            g = h5.create_group('one', 'one')
            g.create_group('two', 'two')
            g = g.create_group('three', 'three')
            g.create_group('four', 'four')
            self.assertEqual(h5['one'].get_group_names(), ['three', 'three/four', 'two'])

    def test_get_dataset_names(self):
        with H5File(mode='w') as h5:
            h5.create_dataset('one', data=1, long_name='long name')
            h5.create_dataset('two', data=1, long_name='long name')
            h5.create_dataset('grp/three', data=1, long_name='long name')
            h5.create_dataset('grp/two', data=1, long_name='long name')
            self.assertEqual(h5.get_dataset_names(), ['grp/three', 'grp/two', 'one', 'two'])

    def test_inspection(self):
        """file (layout/content) check is used to check whether all metadata is set correct
        """
        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.create_dataset(name='test', data=1)
        with H5File(tmpfile, mode='r') as h5:
            n = h5.check(silent=False)
            # missing at root level:
            # title, creation_date, modification_date
            # missing at dataset:
            # units, long_name or standard_name
            self.assertEqual(n, 3)

        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.attrs['title'] = 'testfile'
            h5.create_dataset(name='test', data=1)
        with H5File(tmpfile, mode='r') as h5:
            n = h5.check()
            self.assertEqual(n, 2)

        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.create_group(name='test')

        with H5File(tmpfile, mode='r') as h5:
            n = h5.check(silent=False)
            self.assertEqual(n, 3)


class TestCore(unittest.TestCase):

    def tearDown(self) -> None:
        for fname in Path(__file__).parent.glob('*'):
            if fname.suffix not in ('py', '.py', ''):
                fname.unlink()

    def test_logger(self):
        set_loglevel('debug')
        self.assertTrue(logger.level == logging.DEBUG)
        set_loglevel('info')
        self.assertTrue(logger.level == logging.INFO)

    def test_multi_dim_scales(self):
        fname = generate_temporary_filename(suffix='.hdf')
        with h5py.File(fname, 'w') as h5:
            x = h5.create_dataset('x', data=[0.0, 10.5, 20.13])
            ix = h5.create_dataset('ix', data=[0, 16, 32])
            y = h5.create_dataset('y', data=[0.0, 4.5, 23.13])
            iy = h5.create_dataset('iy', data=[0, 16, 32])

            signal = h5.create_dataset('signal', data=np.ones((3, 3)))
            print(signal[:, :])

            x.make_scale('x')
            ix.make_scale('ix')
            y.make_scale('y')
            iy.make_scale('iy')

            signal.dims[0].attach_scale(h5['x'])
            signal.dims[0].attach_scale(h5['ix'])
            signal.dims[1].attach_scale(h5['y'])
            signal.dims[1].attach_scale(h5['iy'])

        with h5wrapper.H5File(fname) as h5:
            x = h5['x'][:]
            ix = h5['ix'][:]
            s = h5['signal'][:, :]
            print(h5['signal'].dims[0].keys())

    def test_fft(self):
        with H5File(mode='w', title='test file for fft') as h5:
            f = 50  # Hz
            omega = 2 * np.pi * f * ureg.Hz
            h5.create_dataset('time', units='s', long_name='time signal', data=np.arange(0, 0.1, 0.001))
            signal = np.sin(omega * h5.time[:].pint.quantify())
            h5.create_dataset('signal', units='V', long_name='sinusoidal signal',
                              data=signal.pint.dequantify(),
                              attach_scale=h5.time)
            print(h5)
