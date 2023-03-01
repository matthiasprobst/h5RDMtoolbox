"""Testing common functionality across all wrapper class"""

import datetime
import h5py
import numpy as np
import pathlib
import unittest
from datetime import datetime

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import __version__
from h5rdmtoolbox._config import ureg
from h5rdmtoolbox.conventions.layout import H5Layout
from h5rdmtoolbox.wrapper import core, cflike
from h5rdmtoolbox.wrapper.h5attr import WrapperAttributeManager


class TestCommon(unittest.TestCase):

    def setUp(self) -> None:
        self.wrapper_classes = (core.H5File, cflike.H5File)
        self.wrapper_group_classes = (core.H5Group, cflike.H5Group)

    def test_layout(self):
        for wc in self.wrapper_classes:
            with wc(mode='w', layout='H5File') as h5touch:
                self.assertIsInstance(h5touch.layout, H5Layout)
            list_of_registered_layouts = H5Layout.get_registered()
            for lay in list_of_registered_layouts:
                with wc(mode='w', layout=lay) as h5touch:
                    self.assertIsInstance(h5touch.layout, H5Layout)
            for lay in list_of_registered_layouts:
                with wc(mode='w', layout=H5Layout(lay)) as h5touch:
                    self.assertIsInstance(h5touch.layout, H5Layout)
            with self.assertRaises(TypeError):
                with wc(mode='w', layout=123.3):
                    pass

    def test_file_times(self):
        for wc in self.wrapper_classes:
            with wc() as h5:
                now = datetime.now().astimezone()
                file_now = h5.creation_time
                self.assertTrue(abs((file_now - now).total_seconds()) < 1)

    def test_create_group(self):
        """testing the creation of groups"""
        for wc, gc in zip(self.wrapper_classes, self.wrapper_group_classes):
            with wc() as h5:
                self.assertEqual(h5.mode, 'r+')
                grp = h5.create_group('testgrp')
                self.assertIsInstance(grp, gc)

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

        h5tbx.use('default')

        imgreader = ImgReader('testdir')
        with h5tbx.H5File() as h5:
            ds = h5.create_dataset_from_image(imgreader, 'testimg', axis=0)
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))
            # reset imgreader
            imgreader._index = 0
            ds = h5.create_dataset_from_image(imgreader, 'testimg2', axis=-1)
            self.assertEqual(ds.shape, (20, 10, 5))
            self.assertEqual(ds.chunks, (20, 10, 1))

        # write more tests for create_dataset_from_image:
        with h5tbx.H5File() as h5:
            ds = h5.create_dataset_from_image([np.random.random((20, 10))] * 5,
                                              'testimg', axis=0)
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))

        imgreader._index = 0
        h5tbx.use('cflike')
        with h5tbx.H5File() as h5:
            ds = h5.create_dataset_from_image(imgreader, 'testimg', axis=0,
                                              units='', long_name='test')
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))
            # reset imgreader
            imgreader._index = 0
            ds = h5.create_dataset_from_image(imgreader, 'testimg2', axis=-1,
                                              units='', long_name='test')
            self.assertEqual(ds.shape, (20, 10, 5))
            self.assertEqual(ds.chunks, (20, 10, 1))

        # write more tests for create_dataset_from_image:
        with h5tbx.H5File() as h5:
            ds = h5.create_dataset_from_image([np.random.random((20, 10))] * 5,
                                              'testimg', axis=0, units='', long_name='test')
            self.assertEqual(ds.shape, (5, 20, 10))
            self.assertEqual(ds.chunks, (1, 20, 10))

    def test_attrs(self):
        for CLS, WRPGroup in zip(self.wrapper_classes, self.wrapper_group_classes):
            with CLS() as h5:
                # root attributes
                h5.attrs['a_tuple'] = (1, 2, 'awd', {'k': 'v', 'k2': 2})
                t = h5.attrs['a_tuple']
                self.assertIsInstance(t, tuple)
                self.assertEqual(t, (1, 2, 'awd', {'k': 'v', 'k2': 2}))

                h5.attrs['a_list'] = [1, 2, 'awd', {'k': 'v', 'k2': 2}]
                t = h5.attrs['a_list']
                self.assertIsInstance(t, list)
                self.assertEqual(t, [1, 2, 'awd', {'k': 'v', 'k2': 2}])
                h5.attrs.rename('a_list', 'a_new_list')
                t = h5.attrs['a_new_list']
                self.assertIsInstance(t, list)
                self.assertEqual(t, [1, 2, 'awd', {'k': 'v', 'k2': 2}])

                h5.attrs['an_attr'] = 'a_string'
                self.assertEqual(h5.attrs['an_attr'], 'a_string')
                h5.attrs['mean'] = 1.2
                self.assertEqual(h5.attrs['mean'], 1.2)

                test_vals = ('1.2m', '1.2 m', '1.2 [m]', '1.2 (m)')
                for test_val in test_vals:
                    h5.attrs['mean_with_unit'] = test_val
                    self.assertEqual(h5.attrs['mean_with_unit'], test_val)
                    attrs_with_unit = h5.attrs['mean_with_unit'].to_pint()
                    self.assertEqual(f"{h5.attrs['mean_with_unit'].to_pint()}", '1.2 m')
                    h5tbx.config.ureg_format = 'L~'
                    self.assertEqual(f"{h5.attrs['mean_with_unit'].to_pint()}",
                                     '\\begin{pmatrix}1.2\\end{pmatrix}\\ \\mathrm{m}')
                    h5tbx.config.ureg_format = 'C~'
                    self.assertEqual(f"{h5.attrs['mean_with_unit'].to_pint()}", '1.2 m')
                    self.assertEqual(attrs_with_unit, ureg(test_val))
                    h5.attrs['mean_with_unit'] = attrs_with_unit
                    self.assertEqual(h5.attrs['mean_with_unit'], str(ureg(test_val)))

                self.assertEqual(h5.attrs.get('non_existing_attribute'), None)

            hdf_filename = h5.hdf_filename
            with h5py.File(hdf_filename, 'r+') as h5:
                # dataset attributes
                ds = h5.create_dataset('ds', shape=())

            with CLS(hdf_filename, 'r+') as h5:
                ds = h5['ds']
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
                    self.assertEqual(obj.attrs['link_to_group'], '/')
                    self.assertIsInstance(obj.attrs['link_to_group'], str)
                    obj.attrs['link_to_ds'] = ds
                    self.assertEqual(obj.attrs['link_to_ds'], ds.name)
                    self.assertIsInstance(obj.attrs['link_to_ds'], str)
                    obj.attrs['attribute_of_links_to_ds'] = {'ds': ds, 'gr': gr, 'astr': 'test', 'afloat': 3.1}
                    self.assertIsInstance(obj.attrs['attribute_of_links_to_ds'], dict)
                    self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['ds'], h5py.Dataset)
                    self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['gr'], h5py.Group)
                    self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['astr'], str)
                    self.assertIsInstance(obj.attrs['attribute_of_links_to_ds']['afloat'], float)

                self.assertTrue(isinstance(h5.attrs, WrapperAttributeManager))
                self.assertTrue(isinstance(ds.attrs, WrapperAttributeManager))
                self.assertTrue(isinstance(gr.attrs, WrapperAttributeManager))

    def test_Layout(self):

        with h5tbx.H5File() as h5:
            h5.attrs['mandatory_attribute'] = 1

        for wc, gc in zip(self.wrapper_classes, self.wrapper_group_classes):
            with wc() as h5:
                n_issuess = h5.check()
                self.assertIsInstance(n_issuess, int)
                self.assertTrue(n_issuess > 0)

    def test_properties(self):
        for CLS, WRPGroup in zip(self.wrapper_classes, self.wrapper_group_classes):
            with CLS() as h5:
                self.assertIsInstance(h5.creation_time, datetime)
                self.assertTrue('__h5rdmtoolbox_version__' in h5.attrs)
                self.assertEqual(h5.version, __version__)
                self.assertEqual(h5.filesize.units, ureg.byte)
                self.assertIsInstance(h5.hdf_filename, pathlib.Path)
