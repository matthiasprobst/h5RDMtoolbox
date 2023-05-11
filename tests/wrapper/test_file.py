import h5py
import logging
import numpy as np
import pint
import unittest
import yaml
from pathlib import Path

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import config
from h5rdmtoolbox import use
from h5rdmtoolbox.utils import generate_temporary_filename
from h5rdmtoolbox.wrapper import set_loglevel
from h5rdmtoolbox.wrapper.core import Dataset, File, Group

logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')


class TestFile(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        use('tbx')
        use(None)
        with File(mode='w') as h5:
            h5.attrs['one'] = 1
            g = h5.create_group('grp_1')
            g.attrs['one'] = 1
            h5.attrs['two'] = 2
            h5.attrs['three'] = 3
            h5.create_dataset('ds', shape=(4,), attrs=dict(one=1))
            h5.create_group('grp_2')
            h5.create_group('grp_3')
            h5.create_group('grp_X')
            h5.create_dataset('ds1', shape=(3,))
            h5.create_dataset('ds2', shape=(3,))
            h5.create_dataset('dsY', shape=(3,))
            self.test_filename = h5.hdf_filename

        self.lay_filename = generate_temporary_filename(prefix='lay', suffix='.hdf')
        self.other_filename = generate_temporary_filename(prefix='other', suffix='.hdf')

    def tearDown(self) -> None:
        for fname in Path(__file__).parent.glob('*'):
            if fname.suffix not in ('py', '.py', ''):
                fname.unlink()

    def test_offset_scale(self):
        h5tbx.use('tbx')
        with h5tbx.File() as h5:
            ds = h5.create_dataset('pressure',
                                   data=4.3,
                                   units='V',
                                   offset=0.1,
                                   scale=0.2 * pint.Unit('Pa/V'), #0.2 * pint.Unit('Pa/V'),
                                   long_name='pressure')

            self.assertEqual(ds.units, 'V')
            self.assertEqual(ds.scale, pint.Quantity(0.2, 'Pa/V'))
            self.assertEqual(ds.offset, 0.1)
            arr = ds[()]
            self.assertEqual(arr.units, 'Pa')
            print(arr)

    def test_dumps(self):
        with h5tbx.File() as h5:
            h5.dumps()

    def test_create_dataset(self):
        """File has more parameters to pass as H5Base"""
        with File() as h5:
            ds = h5.create_dataset('u', shape=())
            self.assertEqual(ds.name, '/u')

    def test_attrs(self):
        with File(mode='w') as h5:
            h5.create_dataset('ds', shape=(), attrs={'mean': 1.2})

            config.natural_naming = False

            with self.assertRaises(AttributeError):
                self.assertEqual(h5.attrs.mean, 1.2)

            config.natural_naming = True

            h5.attrs.title = 'title of file'
            self.assertEqual(h5.attrs['title'], 'title of file')

            dset = h5.create_dataset('ds', data=1,
                                     attrs={
                                         'long_name': 'a long name',
                                         'a1': 1, 'a2': 'str', 'a3': {'a': 2}
                                     })
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2, 'subdict': {'subkey': 99}}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2, 'subdict': {'subkey': 99}})

    def test_attrs_find(self):
        with File(self.test_filename, mode='r') as h5:
            self.assertEqual(
                h5['/grp_1'],
                h5.find_one(
                    {
                        '$basename': {
                            '$regex': 'grp_[0-1]'
                        }
                    },
                    '$group'
                )
            )
            #
            self.assertListEqual(
                [h5['/grp_1'], h5['/grp_2'], h5['/grp_3']],
                sorted(
                    h5.find(
                        {'$basename': {'$regex': 'grp_[0-3]'}
                         },
                        '$group'
                    )
                )
            )
            self.assertListEqual(
                [h5['/ds1'], h5['/ds2'], ],
                sorted(
                    h5.find(
                        {'$basename': {'$regex': 'ds[0-9]'}},
                        '$dataset')
                )
            )
            self.assertEqual(
                h5['/ds'], h5.find_one({'one': 1}, '$dataset')
            )
            self.assertEqual(
                [h5['/'], h5['/ds'], h5['grp_1']],
                sorted(h5.find({'one': 1}))
            )
            self.assertListEqual(
                [], h5.find({'one': {'$gt': 1}})
            )
            self.assertListEqual(
                [h5['/'], h5['ds'], h5['grp_1']],
                sorted(h5.find({'one': {'$gte': 1}}))
            )

    def test_find_group_data(self):
        with File(self.test_filename, mode='r') as h5:
            self.assertEqual(h5.find({'$basename': 'grp_1'}, '$group')[0],
                             h5.find_one({'$basename': 'grp_1'}, '$group'))
            self.assertEqual([h5['grp_1'], ], h5.find({'$basename': 'grp_1'}, '$group'))
            self.assertEqual(h5['ds'], h5.find_one({'$shape': (4,)}, "$dataset"))
            self.assertEqual(h5.find({'$ndim': 1}, "$dataset")[0], h5.find_one({'$ndim': 1}, "$dataset"))

    def test_find_dataset_data(self):
        with File(self.test_filename, mode='r') as h5:
            self.assertEqual(h5['ds'], h5.find_one({'$basename': 'ds'}, '$dataset'))
            self.assertEqual(h5['ds'], h5.find_one({'$basename': 'ds'}, '$dataset'))
            self.assertEqual([h5['ds'], ], h5.find({'$basename': 'ds'}))
            self.assertEqual([h5['ds'], ], h5.find({'$shape': (4,)}, '$dataset'))
            self.assertEqual(h5['ds'], h5.find_one({'$shape': (4,)}, '$dataset'))
            r = h5.find_one({'$ndim': 1}, '$dataset')
            self.assertEqual(h5['ds'].ndim, 1)
            self.assertIsInstance(h5['ds'], h5py.Dataset)
            self.assertEqual([h5['ds'], h5['ds1'], h5['ds2'], h5['dsY']],
                             sorted(h5.find({'$ndim': 1}, '$dataset')))

    def test_open(self):
        with File(mode='w') as h5:
            pass
        h5.reopen('r+')
        self.assertEqual(h5.mode, 'r+')
        h5.close()

    def test_groups(self):
        with File() as h5:
            groups = h5.get_groups()
            self.assertEqual(groups, [])
            h5.create_group('grp_1', attrs=dict(a=1))
            h5.create_group('grp_2', attrs=dict(a=1))
            h5.create_group('grpXYZ', attrs=dict(b=2))
            h5.create_group('mygrp_2')
            groups = h5.get_groups()
            self.assertEqual(len(groups), 4)
            self.assertEqual(groups, [h5['grpXYZ'], h5['grp_1'], h5['grp_2'], h5['mygrp_2']])
            groups = h5.get_groups('^grp_[0-9]$')
            self.assertEqual(len(groups), 2)
            self.assertEqual(sorted(groups), sorted([h5['grp_1'], h5['grp_2']]))
            self.assertEqual([h5['grp_1'], h5['grp_2']], h5.get_by_attribute('a', 1, recursive=True))

            h5.create_group('grpXYZ/grp123', attrs=dict(a=1))
            self.assertEqual([h5['grpXYZ/grp123'], h5['grp_1'], h5['grp_2'], ],
                             h5.get_by_attribute('a', 1, recursive=True))
            self.assertEqual([h5['grp_1'], h5['grp_2']], h5.get_by_attribute('a', 1, recursive=False))

    def test_tree_structur(self):
        with File() as h5:
            h5.attrs['one'] = 1
            h5.attrs['two'] = 2
            h5.create_dataset('rootds', shape=(2, 40, 3))
            grp = h5.create_group('grp',
                                  attrs={'description': 'group description'})
            grp.create_dataset('grpds',
                               shape=(2, 40, 3))
            tree = h5.get_tree_structure()

    def test_rootparent(self):
        with File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertIsInstance(grp, Group)
            dset = grp.create_dataset('test', data=1, units='', long_name='some long name')
            self.assertIsInstance(dset, Dataset)
            self.assertEqual(dset.rootparent, h5['/'])

    def test_rename(self):
        with File(mode='w') as h5:
            h5.create_dataset('testds',
                              data=np.random.rand(10, 10))
            h5.testds.rename('newname')
            ds = h5.create_dataset('testds_scale',
                                   data=np.random.rand(10, 10))
            ds.make_scale()
            with self.assertRaises(KeyError):
                ds.rename('newname')

    def test_dimension_scales(self):
        with File(mode='w') as h5:
            _ = h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            with self.assertRaises(ValueError):  # because name already exists
                _ = h5.create_dataset('x', data=[1, 2, 3], make_scale=True)
            del h5['x']
            with self.assertRaises(TypeError):
                _ = h5.create_dataset('x', data=[1, 2, 3], make_scale=[1, 2])

    def test_scale_manipulation(self):
        with File(mode='w') as h5:
            h5.create_dataset('x',
                              data=np.random.rand(10),
                              attrs=dict(long_name='x-coordinate',
                                         units='m', ), )
            h5.create_dataset('time', data=np.random.rand(10), attrs=dict(long_name='time', units='s'))
            h5.create_dataset('temp', data=np.random.rand(10), attrs=dict(long_name='temperature', units='K'),
                              attach_scale=((h5['x'], h5['time']),))
            self.assertTrue(h5['temp'].dims[0])
            h5['temp'].set_primary_scale(0, 1)

    def test_xr_dataset(self):
        import xarray as xr
        # from https://docs.xarray.dev/en/v0.9.5/examples/quick-overview.html#datasets
        ds = xr.Dataset({'foo': [1, 2, 3], 'bar': ('x', [1, 2]), 'baz': np.pi})
        ds.foo.attrs['units'] = 'm'
        ds.foo.attrs['long_name'] = 'foo'

        ds.bar.attrs['units'] = 'm'
        ds.bar.attrs['long_name'] = 'bar'

        ds.baz.attrs['units'] = 'm'
        ds.baz.attrs['long_name'] = 'baz'

        with File() as h5:
            h5.create_dataset_from_xarray_dataset(ds)

    def test_attrs(self):
        with File(mode='w') as h5:
            config.natural_naming = False

            with self.assertRaises(AttributeError):
                self.assertEqual(h5.attrs.mean, 1.2)

            config.natural_naming = True

            h5.attrs.title = 'title of file'

            self.assertEqual(h5.attrs['title'], 'title of file')
            #
            # h5.attrs['gr'] = h5['/']
            # self.assertEqual(h5.attrs['gr'].name, '/')

            # h5.attrs.gr2 = h5['/']
            # self.assertEqual(h5.attrs['gr2'].name, '/')

            dset = h5.create_dataset('ds', data=1,
                                     attrs={'a1': 1, 'a2': 'str',
                                            'a3': {'a': 2}})
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

    def test_rootparent(self):
        with File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertEqual(grp.rootparent, h5['/'])

    def test_assign_data_to_existing_dset(self):
        config.natural_naming = True
        with File(mode='w') as h5:
            ds = h5.create_dataset('ds', shape=(2, 3))
            ds[0, 0] = 5
            self.assertEqual(ds[0, 0], 5)

    def test_from_yaml_to_hdf(self):
        dictionary = {
            'datasets': {'boundary/outlet boundary/y':
                             {'data': 2, 'attrs': {'units': 'm', 'standard_name': 'y_coordinate',
                                                   'comment': 'test', 'another_attr': 100.2,
                                                   'array': [1, 2, 3]}}},
            'groups': {'test/grp': {'attrs': {'long_name': 'a test group'}}}
        }
        yaml_file = generate_temporary_filename(suffix='.yaml')
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(dictionary, f)

        hdf_filename = generate_temporary_filename(suffix='.hdf')
        with File(hdf_filename, 'w') as h5:
            h5.from_yaml(yaml_file)
            self.assertIn('test/grp', h5)
            self.assertIn('boundary/outlet boundary/y', h5)
            self.assertTrue(h5['boundary/outlet boundary/y'].attrs['units'], 'm')

    def test_get_group_names(self):
        with File(mode='w') as h5:
            g = h5.create_group('one', 'one')
            g.create_group('two', 'two')
            g = g.create_group('three', 'three')
            g.create_group('four', 'four')
            self.assertEqual(h5['one'].get_group_names(), ['three', 'three/four', 'two'])

    def test_get_dataset_names(self):
        with File(mode='w') as h5:
            h5.create_dataset('one', data=1, attrs=dict(long_name='long name', units=''))
            h5.create_dataset('two', data=1, attrs=dict(long_name='long name', units=''))
            h5.create_dataset('grp/three', data=1, attrs=dict(long_name='long name', units=''))
            h5.create_dataset('grp/two', data=1, attrs=dict(long_name='long name', units=''))
            self.assertEqual(h5.get_dataset_names(),
                             ['grp/three', 'grp/two', 'one', 'two'])

    def test_multi_dim_scales(self):
        fname = generate_temporary_filename(suffix='.hdf')
        with h5py.File(fname, 'w') as h5:
            x = h5.create_dataset('x', data=[0.0, 10.5, 20.13])
            ix = h5.create_dataset('ix', data=[0, 16, 32])
            y = h5.create_dataset('y', data=[0.0, 4.5, 23.13])
            iy = h5.create_dataset('iy', data=[0, 16, 32])

            signal = h5.create_dataset('signal', data=np.ones((3, 3)))

            x.make_scale('x')
            ix.make_scale('ix')
            y.make_scale('y')
            iy.make_scale('iy')

            signal.dims[0].attach_scale(h5['x'])
            signal.dims[0].attach_scale(h5['ix'])
            signal.dims[1].attach_scale(h5['y'])
            signal.dims[1].attach_scale(h5['iy'])

        with File(fname) as h5:
            x = h5['x'][:]
            ix = h5['ix'][:]
            s = h5['signal'][:, :]
