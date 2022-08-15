"""Testing common funcitonality across all wrapper classs"""

import unittest
from datetime import datetime

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.h5wrapper.h5file import H5Group
from h5rdmtoolbox.h5wrapper.h5file import WrapperAttributeManager
from h5rdmtoolbox.h5wrapper.h5flow import H5FlowGroup
from h5rdmtoolbox.h5wrapper.h5piv import H5PIVGroup


class TestCommon(unittest.TestCase):

    def setUp(self) -> None:
        self.wrapper_classes = (h5tbx.H5File, h5tbx.H5Flow, h5tbx.H5PIV)
        self.wrapper_grouclasses = (H5Group, H5FlowGroup, H5PIVGroup)

    def test_file_times(self):
        for wc in self.wrapper_classes:
            with wc() as h5:
                now = datetime.now().astimezone().strftime(h5tbx.conventions.datetime_str)
                self.assertEqual(h5.creation_time, now)

    def test_create_group(self):
        """testing the creation of groups"""
        for wc, gc in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with wc() as h5:
                h5.mode == 'r+'
                grp = h5.create_group('testgrp')
                self.assertIsInstance(grp, gc)

    def test_attrs(self):
        for CLS, WRPGroup in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with CLS() as h5:
                # root attributes
                h5.attrs['an_attr'] = 'a_string'
                self.assertEqual(h5.attrs['an_attr'], 'a_string')
                h5.attrs['mean'] = 1.2
                self.assertEqual(h5.attrs['mean'], 1.2)
                with self.assertRaises(AttributeError):
                    h5.attrs['standard_name'] = 'a_string'
                with self.assertRaises(ValueError):
                    h5.attrs['long_name'] = '1alongname'
                with self.assertRaises(ValueError):
                    h5.attrs['long_name'] = ' 1alongname'
                with self.assertRaises(ValueError):
                    h5.attrs['long_name'] = '1alongname '

                with self.assertRaises(KeyError):
                    h5.attrs['non_existing_attribute']

                # dataset attibutes
                ds = h5.create_dataset('ds', shape=(), long_name='a long name', units='m/s')
                with self.assertRaises(ValueError):
                    ds.attrs['long_name'] = '1alongname'
                with self.assertRaises(ValueError):
                    ds.attrs['long_name'] = ' 1alongname'
                with self.assertRaises(ValueError):
                    ds.attrs['long_name'] = '1alongname '
                ds.attrs['an_attr'] = 'a_string'
                self.assertEqual(ds.attrs['an_attr'], 'a_string')
                ds.attrs['mean'] = 1.2
                self.assertEqual(ds.attrs['mean'], 1.2)

                # group attributes
                gr = h5.create_group('gr')
                gr.attrs['an_attr'] = 'a_string'
                self.assertEqual(gr.attrs['an_attr'], 'a_string')
                gr.attrs['mean'] = 1.2
                self.assertEqual(gr.attrs['mean'], 1.2)

                # special attributes:
                for obj in (h5, ds, gr):
                    obj.attrs['link_to_group'] = h5['/']
                    self.assertEqual(obj.attrs['link_to_group'].name, '/')
                    self.assertIsInstance(obj.attrs['link_to_group'], h5py.Group)
                    obj.attrs['link_to_ds'] = ds
                    self.assertEqual(obj.attrs['link_to_ds'].name, ds.name)
                    self.assertIsInstance(obj.attrs['link_to_ds'], h5py.Dataset)
                    obj.attrs['attibute_of_links_to_ds'] = {'ds': ds, 'gr': gr, 'astr': 'test', 'afloat': 3.1}
                    self.assertIsInstance(obj.attrs['attibute_of_links_to_ds'], dict)
                    self.assertIsInstance(obj.attrs['attibute_of_links_to_ds']['ds'], h5py.Dataset)
                    self.assertIsInstance(obj.attrs['attibute_of_links_to_ds']['gr'], h5py.Group)
                    self.assertIsInstance(obj.attrs['attibute_of_links_to_ds']['astr'], str)
                    self.assertIsInstance(obj.attrs['attibute_of_links_to_ds']['afloat'], float)

                self.assertTrue(isinstance(h5.attrs, WrapperAttributeManager))
                self.assertTrue(isinstance(ds.attrs, WrapperAttributeManager))
                self.assertTrue(isinstance(gr.attrs, WrapperAttributeManager))

                # TODO Fix the following issue:
                h5.non_existing_attribute = 1
                print(h5.non_existing_attribute)

                # self.assertEqual(ds.standard_name, h5tbx.conventions.Empty_Standard_Name_Table)
                ds.standard_name = 'x_velocity'
                self.assertIsInstance(ds.standard_name, h5tbx.conventions.StandardizedName)
                self.assertIsInstance(ds.attrs['standard_name'], str)
                self.assertEqual(ds.attrs['standard_name'], 'x_velocity')

    def test_Layout(self):

        with h5tbx.H5File() as h5:
            h5.attrs['mandatory_attribute'] = 1

        for wc, gc in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with wc() as h5:
                n_issuess = h5.check(silent=True)
                self.assertIsInstance(n_issuess, int)
                self.assertTrue(n_issuess > 0)

    def test_properties(self):
        import datetime
        from h5rdmtoolbox.conventions.data import DataSourceType
        from h5rdmtoolbox import __version__
        from pint_xarray import unit_registry as ureg
        import pathlib

        for CLS, WRPGroup in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with CLS() as h5:
                self.assertIsInstance(h5.creation_time, datetime.datetime)
                self.assertIsInstance(h5.data_source_type, DataSourceType)
                self.assertEqual(h5.data_source_type, DataSourceType.none)
                h5.attrs['data_source_type'] = 'experimental'
                self.assertEqual(h5.data_source_type, DataSourceType.experimental)
                self.assertEqual(h5.title, None)
                h5.title = 'my title'
                self.assertEqual(h5.title, 'my title')
                self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
                self.assertEqual(h5.version, __version__)
                self.assertEqual(h5.filesize.units, ureg.byte)
                self.assertIsInstance(h5.hdf_filename, pathlib.Path)

    def test_open_wrapper(self):
        from h5rdmtoolbox.utils import generate_temporary_filename
        from h5rdmtoolbox.h5wrapper import open_wrapper
        for CLS, WRPGroup in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with CLS() as h5:
                old_filename = h5.hdf_filename
                new_filename = generate_temporary_filename(suffix='.hdf')
                self.assertFalse(new_filename.exists())
                new_filename = h5.moveto(new_filename)
                self.assertTrue(new_filename.exists())
                self.assertNotEqual(old_filename, h5.filename)
                self.assertNotEqual(old_filename, h5.hdf_filename)
                with self.assertRaises(FileExistsError):
                    h5.moveto(new_filename)
                self.assertTrue(new_filename.exists())
                self.assertFalse(old_filename.exists())

            with CLS() as h5:
                old_filename = h5.hdf_filename
                new_filename = generate_temporary_filename(suffix='.hdf')
                new_filename = h5.saveas(new_filename)
                self.assertTrue(new_filename.exists())
                self.assertTrue(old_filename.exists())

            with CLS() as h5:
                filename = h5.hdf_filename
            obj = open_wrapper(filename)
            self.assertIsInstance(obj, CLS)

        with CLS() as h5:
            del h5.attrs['__wrcls__']
            filename = h5.hdf_filename
        obj = open_wrapper(filename)
        self.assertIsInstance(obj, h5tbx.H5File)

    def test_create_dataset(self):
        from h5rdmtoolbox.conventions import UnitsError
        from h5rdmtoolbox.conventions import Empty_Standard_Name_Table
        for wc, gc in zip(self.wrapper_classes, self.wrapper_grouclasses):
            with wc(standard_name_table=Empty_Standard_Name_Table) as h5:
                self.assertEqual(h5.standard_name_table.name, Empty_Standard_Name_Table.name)
                h5tbx.config.require_units = True
                with self.assertRaises(UnitsError):
                    h5.create_dataset(name='x', standard_name='x_coordinate', data=1)
                h5tbx.config.require_units = False
                h5.create_dataset(name='x', standard_name='x_coordinate', data=1, units=None)
                h5tbx.config.require_units = True
                h5.create_dataset(name='x1', standard_name='x_coordinate', data=1, units='m')
                h5.create_dataset(name='x2', standard_name='XCoord', data=1, units='m')
                h5.create_dataset(name='x3', standard_name='CoordinateX', data=1, units='m')
                h5.create_dataset(name='x4', standard_name='NoRealStdName', data=1, units='m')
