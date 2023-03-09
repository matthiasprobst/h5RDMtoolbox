import h5py
import logging
import numpy as np
import pint.errors
import unittest
import xarray as xr
import yaml
from pathlib import Path

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import config
from h5rdmtoolbox._config import ureg
from h5rdmtoolbox.conventions.cflike import StandardNameTable
from h5rdmtoolbox.conventions.cflike import standard_name as sn
from h5rdmtoolbox.conventions.layout import H5Layout
from h5rdmtoolbox.errors import StandardNameError
from h5rdmtoolbox.utils import generate_temporary_filename, touch_tmp_hdf5_file
from h5rdmtoolbox.wrapper import cflike
from h5rdmtoolbox.wrapper import set_loglevel
from h5rdmtoolbox.wrapper.cflike import Dataset
from h5rdmtoolbox.wrapper.cflike import Group
from h5rdmtoolbox.wrapper.h5attr import AttributeString

logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')


class TestH5CFLikeFile(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        h5tbx.use('cflike')
        with h5tbx.File() as h5:
            self.assertIsInstance(h5, cflike.File)
        with h5tbx.File(mode='w', title='dwa') as h5:
            h5.attrs['one'] = 1
            g = h5.create_group('grp_1')
            g.attrs['one'] = 1
            h5.attrs['two'] = 2
            h5.attrs['three'] = 3
            h5.create_dataset('ds', shape=(4,), units='', long_name='long name', attrs=dict(one=1))
            h5.create_group('grp_2')
            h5.create_group('grp_3')
            h5.create_group('grp_X')
            h5.create_dataset('ds1', shape=(3,), units='', long_name='long name')
            h5.create_dataset('ds2', shape=(3,), units='', long_name='long name')
            h5.create_dataset('dsY', shape=(3,), units='', long_name='long name')
            self.test_filename = h5.hdf_filename

        self.lay_filename = generate_temporary_filename(prefix='lay', suffix='.hdf')
        self.other_filename = generate_temporary_filename(prefix='other', suffix='.hdf')

    def test_H5File(self):
        self.assertEqual(str(h5tbx.File), "<class 'h5rdmtoolbox.File'>")
        with h5tbx.File() as h5:
            self.assertEqual(h5.__str__(), "<class 'h5rdmtoolbox.File' convention: cflike>")
        self.assertEqual(h5tbx.File.Dataset(), cflike.Dataset)
        self.assertEqual(h5tbx.File.Group(), cflike.Group)

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

            h5.create_dataset('ds', data=1, standard_name='x_coordinate', units='m')
            sn = h5['ds'].attrs['standard_name']
            h5.attrs['sn'] = sn
            sn = h5['ds'].standard_name
            h5.attrs['sn'] = sn

    def test_str(self):
        strrepr = h5tbx.File().__str__()
        self.assertEqual(strrepr, "<class 'h5rdmtoolbox.File' convention: cflike>")

    def test_layout(self):
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            grp = h5.create_group('grp')
            grp.attrs['__check_isoptional__'] = True
        with h5py.File(self.other_filename, 'w') as other:
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

        with lay.File(mode='w') as h5:
            grp = h5.create_group('grp')
        with h5py.File(self.other_filename, 'w') as other:
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)
        self.assertDictEqual(lay._issues_list[0], {'path': '/grp', 'obj_type': 'group', 'issue': 'missing'})

    def test_layout_regrex(self):
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            grp = h5.create_group('re:plane[0-9]')
            subgrp = grp.create_group('subgroup')
            # grp.attrs['__check_isoptional__'] = False

        with h5py.File(self.other_filename, 'w') as other:
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

        with h5py.File(self.other_filename, 'w') as other:
            other.create_group('plane0')
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

        with lay.File(mode='w') as h5:
            grp = h5.create_group('re:plane[0-9]')
            grp.attrs['__check_isoptional__'] = True
            subgrp = grp.create_group('subgroup')  # mandatory if plane[0-9] exists

        with h5py.File(self.other_filename, 'w') as other:
            # plane[0-9] doe does not exist. as it is optional no issues found
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

    def test_layout_altgrp1(self):
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            # ds = h5.create_dataset('u.alt:re:plane[0-9]', shape=1)
            ds = h5.create_dataset('u', shape=1)
            ds.attrs['__alternative_source_group__'] = 'plane0'

        with h5py.File(self.other_filename, 'w') as other:
            ds = other.create_dataset('u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

    def test_layout_altgrp2(self):
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            ds = h5.create_dataset('u', shape=1)
            ds.attrs['__alternative_source_group__'] = 'plane0'

        with h5py.File(self.other_filename, 'w') as other:
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

        with h5py.File(self.other_filename, 'w') as other:
            other.create_dataset('plane0/u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

        with h5py.File(self.other_filename, 'w') as other:
            ds = other.create_dataset('plane1/u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

    def test_layout_altgrp3(self):
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            ds = h5.create_dataset('u', shape=1)
            ds.attrs['__alternative_source_group__'] = 're:plane[0-9]'

        with h5py.File(self.other_filename, 'w') as other:
            ds = other.create_dataset('u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

        with h5py.File(self.other_filename, 'w') as other:
            ds = other.create_dataset('plane0/u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

        with h5py.File(self.other_filename, 'w') as other:
            ds = other.create_dataset('plane0/u', shape=1)
            ds = other.create_dataset('plane1/u', shape=1)
            ds = other.create_dataset('plane1297/u', shape=1)
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

    def test_layout_altgrp4(self):
        """alternative groups"""
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            h5.create_group('pivpar')
            h5['pivpar'].attrs['__alternative_source_group__'] = 'plane0'

        with h5py.File(self.other_filename, 'w') as other:
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

        with h5py.File(self.other_filename, 'w') as other:
            other.create_group('pivpar')
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

        with h5py.File(self.other_filename, 'w') as other:
            other.create_group('plane0/pivpar')
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)

    def test_layout_altgrp5(self):
        """alternative groups"""
        lay = H5Layout(self.lay_filename)
        with lay.File(mode='w') as h5:
            gr = h5.create_group('pivpar')
            gr.attrs['__alternative_source_group__'] = 're:plane[0-9]'
            gr.attrs['important'] = 'attribute'

        # with h5py.File(self.other_filename, 'w') as other:
        #     lay.check(other)
        # self.assertEqual(lay.n_issues, 1)
        #
        with h5py.File(self.other_filename, 'w') as other:
            gr = other.create_group('pivpar')
            gr.attrs['important'] = 'attribute'
            lay.check(other)
        self.assertEqual(lay.n_issues, 0)
        #
        with h5py.File(self.other_filename, 'w') as other:
            gr = other.create_group('plane0/pivpar')
            gr.attrs['important'] = 'attribute'
            other.create_group('plane1/pivpar')
            lay.check(other)
        self.assertEqual(lay.n_issues, 1)

        # with h5py.File(self.other_filename, 'w') as other:
        #     other.create_group('plane000/pivpar')
        #     lay.check(other)
        # self.assertEqual(lay.n_issues, 0)

    def test_empty_convention(self):
        with h5tbx.File() as h5:
            self.assertIsInstance(h5.standard_name_table, StandardNameTable)
            self.assertEqual(h5.standard_name_table.version_number, 0)
            self.assertEqual(h5.standard_name_table.name, 'EmptyStandardNameTable')

    def test_create_dataset(self):
        """File has more parameters to pass as H5Base"""
        with h5tbx.File() as h5:
            with self.assertRaises(RuntimeError):
                _ = h5.create_dataset('u', shape=(), units='m/s')
        with h5tbx.File() as h5:
            ds = h5.create_dataset('u', shape=(), long_name='velocity', units='')
            self.assertEqual(ds.name, '/u')
            self.assertEqual(ds.attrs['units'], '')
            self.assertEqual(ds.attrs['long_name'], 'velocity')
        with h5tbx.File() as h5:
            ds = h5.create_dataset('velocity', shape=(), standard_name='x_velocity', units='')
            self.assertEqual(ds.attrs['units'], '')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
        with h5tbx.File() as h5:
            ds = h5.create_dataset('velocity', shape=(),
                                   standard_name='x_velocity',
                                   units='m/s')
            self.assertEqual(ds.attrs['units'], 'm/s')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')
        da = xr.DataArray(data=[1, 2, 3], attrs={'units': 'm/s'})
        with h5tbx.File() as h5:
            with self.assertRaises(RuntimeError):
                _ = h5.create_dataset('velocity', data=da)

        da = xr.DataArray(data=[1, 2, 3], attrs={'units': 'm/s', 'standard_name': 'x_velocity'})
        with h5tbx.File() as h5:
            ds = h5.create_dataset('velocity', data=da)
            self.assertEqual(ds.attrs['units'], 'm/s')
            self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_create_string_dataset(self):
        with h5tbx.File() as h5:
            ds = h5.create_string_dataset('test', data='test')
            self.assertEqual(ds[()], 'test')

    def test_create_group(self):
        """testing the creation of groups"""
        with h5tbx.File() as h5:
            grp = h5.create_group('testgrp2', long_name='a long name')
            self.assertEqual(grp.attrs['long_name'], 'a long name')
            self.assertEqual(grp.long_name, 'a long name')

    def test_Layout(self):
        with h5tbx.File() as h5:
            h5.create_dataset('test', shape=(3,), long_name='daadw', units='')
            h5.create_dataset('testgrp/ds2', shape=(30,), long_name='daadw', units='')
            n_issuess = h5.check()

    def test_attrs(self):
        with h5tbx.File(mode='w') as h5:
            convention = StandardNameTable(name='empty',
                                           table={'x_velocity': {'description': '',
                                                                 'units': 'm/s'}},
                                           version_number=0,
                                           valid_characters='[^a-zA-Z0-9_]',
                                           institution='', contact='a.b@test.com')
            h5.standard_name_table = convention
            self.assertIsInstance(h5.standard_name_table, StandardNameTable)
            ds = h5.create_dataset('ds', shape=(), long_name='x_velocity', units='m/s')
            with self.assertRaises(StandardNameError):
                ds.attrs['standard_name'] = ' x_velocity'
            sn.STRICT = False
            ds.attrs['standard_name'] = 'x_velocityyy'
            with self.assertRaises(StandardNameError):
                ds.attrs['standard_name'] = '!x_velocityyy'
            sn.STRICT = True
            with self.assertRaises(StandardNameError):
                ds.attrs['standard_name'] = 'x_velocityyy'
            del h5['ds']

            config.natural_naming = False

            with self.assertRaises(AttributeError):
                self.assertEqual(h5.attrs.mean, 1.2)

            config.natural_naming = True

            h5.attrs.title = 'title of file'
            self.assertEqual(h5.attrs['title'], 'title of file')

            # h5.attrs['gr'] = h5['/']
            # self.assertEqual(h5.attrs['gr'].name, '/')

            # h5.attrs.gr2 = h5['/']
            # self.assertEqual(h5.attrs['gr2'].name, '/')

            dset = h5.create_dataset('ds', data=1, long_name='a long name', units='', attrs={'a1': 1, 'a2': 'str',
                                                                                             'a3': {'a': 2}})
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            # h5.attrs['ds'] = dset
            # self.assertEqual(h5.attrs['ds'], dset)
            # self.assertIsInstance(h5.attrs['ds'], Dataset)

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2, 'subdict': {'subkey': 99}}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2, 'subdict': {'subkey': 99}})

    def test_attrs_find(self):
        with h5tbx.File(self.test_filename, mode='r') as h5:
            self.assertEqual(
                h5['/grp_1'],
                h5.find_one(
                    {
                        '$basename': {
                            '$regex': 'grp_[0-9]'
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
                        {'$basename': {'$regex': 'grp_[0-9]'}
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
        with h5tbx.File(self.test_filename, mode='r') as h5:
            self.assertEqual(h5['grp_1'], h5.find_one({'$basename': 'grp_1'}, '$group'))
            self.assertEqual([h5['grp_1'], ], h5.find({'$basename': 'grp_1'}, '$group'))
            self.assertEqual(h5['ds'], h5.find_one({'$shape': (4,)}, "$dataset"))
            self.assertEqual(h5['ds'], h5.find_one({'$ndim': 1}, "$dataset"))

    def test_find_dataset_data(self):
        with h5tbx.File(self.test_filename, mode='r') as h5:
            self.assertEqual(h5['ds'], h5.find_one({'$basename': 'ds'}, '$dataset'))
            self.assertEqual(h5['ds'], h5.find_one({'$basename': 'ds'}, '$dataset'))
            self.assertEqual([h5['ds'], ], h5.find({'$basename': 'ds'}))
            with self.assertRaises(AttributeError):
                self.assertEqual([h5['ds'], ], h5.find({'$shape': (4,)}))
            with self.assertRaises(AttributeError):
                self.assertEqual([h5['ds'], ], h5.find({'$shape': (4,)}, '$group'))
            self.assertEqual([h5['ds'], ], h5.find({'$shape': (4,)}, ignore_attribute_error=True))
            self.assertEqual(h5['ds'], h5.find_one({'$shape': (4,)}, objfilter='$dataset'))
            self.assertEqual(h5['ds'], h5.find_one({'$ndim': 1}, '$dataset'))
            self.assertEqual([h5['ds'], h5['ds1'], h5['ds2'], h5['dsY']],
                             sorted(h5.find({'$ndim': 1}, '$dataset')))

    def test_H5File_and_standard_name(self):
        with self.assertRaises(FileNotFoundError):
            with h5tbx.File(mode='w', standard_name_table='wrong file name'):
                pass
        with h5tbx.File(mode='w', standard_name_table=None) as h5:
            self.assertIsInstance(h5.standard_name_table, StandardNameTable)

    def test_open(self):
        with h5tbx.File(mode='w') as h5:
            pass
        h5.reopen('r+')
        self.assertEqual(h5.mode, 'r+')
        h5.close()

    def test_create_group(self):
        with h5tbx.File() as h5:
            grp = h5.create_group('test_grp')
            self.assertIsInstance(grp, Group)
            grp = grp.create_group('test_grp')
            self.assertIsInstance(grp, Group)

    def test_groups(self):
        with h5tbx.File() as h5:
            groups = h5.get_groups()
            self.assertEqual(groups, [])
            h5.create_group('grp_1', attrs=dict(a=1))
            h5.create_group('grp_2', attrs=dict(a=1))
            h5.create_group('grpXYZ', attrs=dict(b=2))
            h5.create_group('mygrp_2')
            groups = h5.get_groups()
            self.assertEqual(groups, [h5['grpXYZ'], h5['grp_1'], h5['grp_2'], h5['mygrp_2']])
            groups = h5.get_groups('^grp_[0-9]$')
            self.assertEqual(sorted(groups), sorted([h5['grp_1'], h5['grp_2']]))
            self.assertEqual(sorted([h5['grp_1'], h5['grp_2']]), sorted(h5.get_by_attribute('a', 1, recursive=True)))

            h5.create_group('grpXYZ/grp123', attrs=dict(a=1))
            self.assertEqual(sorted([h5['grpXYZ/grp123'], h5['grp_1'], h5['grp_2'], ]),
                             sorted(h5.get_by_attribute('a', 1, recursive=True)))
            self.assertEqual(sorted([h5['grp_1'], h5['grp_2']]),
                             sorted(h5.get_by_attribute('a', 1, recursive=False)))

    def test_tree_structure(self):
        with h5tbx.File() as h5:
            h5.attrs['one'] = 1
            h5.attrs['two'] = 2
            h5.create_dataset('rootds', shape=(2, 40, 3), units='', long_name='long name',
                              standard_name='a_standard_name')
            grp = h5.create_group('grp', attrs={'description': 'group description'})
            grp.create_dataset('grpds', shape=(2, 40, 3), units='', long_name='long name',
                               standard_name='a_standard_name')
            tree = h5.get_tree_structure()
            # from pprint import pprint
            # pprint(tree)

    def test_rootparent(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertIsInstance(grp, Group)
            dset = grp.create_dataset('test', data=1, units='', long_name='some long name')
            self.assertIsInstance(dset, Dataset)
            self.assertEqual(dset.rootparent, h5['/'])

    def test_rename(self):
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('testds', units='', long_name='random', data=np.random.rand(10, 10))
            h5.testds.rename('newname')
            ds = h5.create_dataset('testds_scale', units='', long_name='random long name', data=np.random.rand(10, 10))
            ds.make_scale()
            with self.assertRaises(KeyError):
                ds.rename('newname')

    def test_to_unit(self):
        with h5tbx.File(mode='w') as h5:
            dset = h5.create_dataset('temp', units='degC', long_name='temperature dataset', data=20)
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('degC'))
            self.assertEqual(float(dset[()].values), 20)
            dset.to_units('K', inplace=True)
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('K'))
            self.assertEqual(float(dset[()].values), 293)
            dset.to_units('degC', inplace=True)
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('degC'))
            dset_K = dset.to_units('K', inplace=False)
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('degC'))
            self.assertEqual(ureg.Unit(dset_K.units), ureg.Unit('K'))

            dset = h5.create_dataset('temp2', units='degC',
                                     long_name='temperature dataset', data=[20, 30])
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('degC'))
            self.assertEqual(float(dset[()].values[0]), 20)
            self.assertEqual(float(dset[()].values[1]), 30)
            dset.to_units('K', inplace=True)
            self.assertEqual(ureg.Unit(dset.units), ureg.Unit('K'))
            self.assertEqual(float(dset[()].values[0]), 293)
            self.assertEqual(float(dset[()].values[1]), 303)

    def test_scale_manipulation(self):
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('x', long_name='x-coordinate', units='m', data=np.random.rand(10))
            h5.create_dataset('time', long_name='time', units='s', data=np.random.rand(10))
            h5.create_dataset('temp', long_name='temperature', units='K', data=np.random.rand(10),
                              attach_scale=((h5['x'], h5['time']),))
            self.assertTrue(h5['temp'].dims[0])
            h5['temp'].set_primary_scale(0, 1)

    def test_xr_dataset(self):
        # from https://docs.xarray.dev/en/v0.9.5/examples/quick-overview.html#datasets
        ds = xr.Dataset({'foo': [1, 2, 3], 'bar': ('x', [1, 2]), 'baz': np.pi})
        ds.foo.attrs['units'] = 'm'
        ds.foo.attrs['long_name'] = 'foo'

        ds.bar.attrs['units'] = 'm'
        ds.bar.attrs['long_name'] = 'bar'

        ds.baz.attrs['units'] = 'm'
        ds.baz.attrs['long_name'] = 'baz'

        with h5tbx.File() as h5:
            h5.create_dataset_from_xarray_dataset(ds)

    def test_attrs(self):
        with h5tbx.File(mode='w') as h5:
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

            dset = h5.create_dataset('ds', data=1, long_name='a long name', attrs={'a1': 1, 'a2': 'str',
                                                                                   'a3': {'a': 2}},
                                     units='')
            self.assertEqual(dset.attrs.get('a1'), 1)
            self.assertEqual(dset.attrs.get('a2'), 'str')

            h5.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(h5.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

            # h5.attrs['ds'] = dset
            # self.assertEqual(h5.attrs['ds'], dset)
            # self.assertIsInstance(h5.attrs['ds'], Dataset)

            dset.attrs['a dict'] = {'key1': 'value1', 'key2': 1239.2}
            self.assertDictEqual(dset.attrs['a dict'], {'key1': 'value1', 'key2': 1239.2})

    def test_units(self):
        with h5tbx.File(mode='w', title='semantic test file') as h5:
            ds = h5.create_dataset(name='x', standard_name='x_coordinate', shape=(10, 20), units='')
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
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('grp1/grp2/grp3')
            self.assertEqual(grp.rootparent, h5['/'])

    def test_create_group(self):
        with h5tbx.File(mode='w') as h5:
            grp = h5.create_group('group')
            self.assertEqual(h5.long_name, None)
            grp.long_name = 'long name of group'
            self.assertEqual(grp.long_name, 'long name of group')

    def test_assign_data_to_existing_dset(self):
        config.natural_naming = True
        with h5tbx.File(mode='w') as h5:
            ds = h5.create_dataset('ds', shape=(2, 3), long_name='a long name', units='')
            ds[0, 0] = 5
            self.assertEqual(ds[0, 0], 5)

    def test_create_dataset_from_xarray(self):
        config.natural_naming = True
        with h5tbx.File(mode='w') as h5:
            z = xr.DataArray(name='z', data=-1,
                             attrs=dict(units='m', standard_name='z_coordinate'))
            x = xr.DataArray(name='x', data=[1, 2, 3], dims='x',
                             attrs=dict(units='m', standard_name='x_coordinate'))
            u = xr.DataArray(name='u', data=[1, 1, 1], coords={'x': x, 'z': z}, dims=('x',),
                             attrs={'units': 'invalid units', 'long_name': 'x-velocity'})
            with self.assertRaises(pint.errors.UndefinedUnitError):
                h5.create_dataset('u', data=u)
            u = xr.DataArray(name='u', data=[1, 1, 1], coords={'x': x, 'z': z}, dims=('x',),
                             attrs={'units': 'm/s', 'long_name': 'x-velocity'})
            h5.create_dataset('u', data=u)

            u = h5.u[:]
            self.assertTrue('COORDINATES' not in u.attrs)
            self.assertTrue('COORDINATES' in h5['u'].attrs)

            time = xr.DataArray(dims='time', data=np.linspace(0, 1, 5),
                                attrs={'standard_name': 'time', 'units': 's'})
            h5['xr_data'] = xr.DataArray(dims='time',
                                         data=np.random.rand(5, ),
                                         coords={'time': time},
                                         attrs={'long_name': 'xr data', 'units': 's'})
            self.assertEqual(h5['xr_data'].shape, (5,))
            self.assertIn('time', h5)
            self.assertEqual(h5.xr_data.dims[0][0], h5['time'])

            with self.assertRaises(ValueError):
                h5['xr_data2'] = xr.DataArray(dims='time',
                                              data=np.random.rand(5, ),
                                              coords={'time': np.linspace(0, 2, 5)})
            h5['xr_data2'] = xr.DataArray(dims='time',
                                          data=np.random.rand(5, ),
                                          coords={'time': time},
                                          attrs={'long_name': 'xr data with same time coord', 'units': 's'})
            self.assertIn('long_name', h5['xr_data2'].attrs)

            xrtime2 = xr.DataArray(dims='time2', data=np.linspace(0, 3, 5),
                                   attrs={'standard_name': 'time', 'units': 's'})
            ds = h5.create_dataset('xr_data3', data=xr.DataArray(dims='time2',
                                                                 data=np.random.rand(5, ),
                                                                 coords={'time2': xrtime2},
                                                                 attrs={'standard_name': 'time', 'units': 's'}))
            with self.assertRaises(ValueError):
                # dataset "time" already exists
                h5.create_dataset('xr_data4', data=xr.DataArray(dims='time',
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
        with h5tbx.File(hdf_filename, 'w') as h5:
            h5.from_yaml(yaml_file)
            self.assertIn('test/grp', h5)
            self.assertIn('boundary/outlet boundary/y', h5)
            self.assertTrue(h5['boundary/outlet boundary/y'].units, 'm')

    def test_get_by_attribute(self):
        with h5tbx.File(mode='w') as h5:
            lname = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(lname, [])

            h5.create_dataset('test', data=2, units='m',
                              long_name='a long name')
            lname = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(lname, [h5['test'], ])
            h5.create_dataset('grp/test', data=2, units='m',
                              long_name='a long name 2')
            lname = h5.get_datasets_by_attribute('long_name')
            self.assertEqual(lname, [h5['grp/test'], h5['test']])
            lname = h5.get_datasets_by_attribute('long_name',
                                                 'a long name')
            self.assertEqual(lname, [h5['test'], ])

            h5['grp'].long_name = 'grp1'
            r = h5.get_groups_by_attribute('long_name')
            self.assertEqual(r, [h5['grp'], ])

    def test_get_group_names(self):
        with h5tbx.File(mode='w') as h5:
            g = h5.create_group('one', 'one')
            g.create_group('two', 'two')
            g = g.create_group('three', 'three')
            g.create_group('four', 'four')
            self.assertEqual(h5['one'].get_group_names(), ['three', 'three/four', 'two'])

    def test_get_dataset_names(self):
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('one', data=1, long_name='long name', units='')
            h5.create_dataset('two', data=1, long_name='long name', units='')
            h5.create_dataset('grp/three', data=1, long_name='long name', units='')
            h5.create_dataset('grp/two', data=1, long_name='long name', units='')
            self.assertEqual(h5.get_dataset_names(), ['grp/three', 'grp/two', 'one', 'two'])

    def test_inspection(self):
        """file (layout/content) check is used to check whether all metadata is set correct
        """
        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.create_dataset(name='test', data=1)
        with h5tbx.File(tmpfile, mode='r') as h5:
            n = h5.check()
            # missing at root level:
            # title
            # missing at dataset:
            # units, long_name or standard_name
            self.assertEqual(n, 1)

        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.attrs['title'] = 'testfile'
            h5.create_dataset(name='test', data=1)
        with h5tbx.File(tmpfile, mode='r') as h5:
            n = h5.check()
            self.assertEqual(n, 0)
        return

        tmpfile = touch_tmp_hdf5_file()
        with h5py.File(tmpfile, mode='w') as h5:
            h5.create_group(name='test')

        with h5tbx.File(tmpfile, mode='r') as h5:
            n = h5.check()
            self.assertEqual(n, 2)

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

        with h5tbx.File(fname) as h5:
            x = h5['x'][:]
            ix = h5['ix'][:]
            s = h5['signal'][:, :]

    def test_repr(self):
        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, units='m', long_name='a test dataset', dtype='int64')
            self.assertEqual(h5tbx.wrapper.cflike.CFLikeHDF5StructureStrRepr().__0Ddataset__('test', h5['test']),
                             '\x1b[1mtest\x1b[0m 1 [m], dtype: int64')
            h5.create_dataset('test2', data=1, units='m', long_name='a test dataset', dtype='int32')
            self.assertEqual(h5tbx.wrapper.cflike.CFLikeHDF5StructureStrRepr().__0Ddataset__('test2', h5['test2']),
                             '\x1b[1mtest2\x1b[0m 1 [m], dtype: int32')


    def tearDown(self) -> None:
        for fname in Path(__file__).parent.glob('*'):
            if fname.suffix not in ('py', '.py', ''):
                fname.unlink()
