import glob
import os
import unittest
from pathlib import Path
from h5rdmtoolbox.utils import generate_temporary_filename
from shutil import rmtree

from h5rdmtoolbox import h5database
from h5rdmtoolbox.h5database import config
from h5rdmtoolbox.h5database import h5repo
from h5rdmtoolbox.h5database.filter_classes import *
from h5rdmtoolbox.h5database.filter_classes import Entry
from h5rdmtoolbox.h5database.h5repo import H5repo
from h5rdmtoolbox.h5database.tutorial import build_test_repo
from h5rdmtoolbox.h5wrapper import H5File
from h5rdmtoolbox.h5wrapper import set_loglevel

h5database.use(Path(__file__).parent.joinpath('test_h5database.yaml'))

set_loglevel('error')


class H5TestClass(H5File):

    @property
    def vfr(self):
        """returns volume flow_utils rate"""
        return self['operation_point/vfr'][:]


class TestH5Repo(unittest.TestCase):

    def setUp(self) -> None:
        datapath = Path(h5database.config["datapath"])
        if datapath.is_dir():
            rmtree(h5database.config['datapath'])
        self.n_test_files = 100
        build_test_repo(datapath, self.n_test_files)
        repo_filename = h5repo.build_repo_toc(datapath)
        self.repo_filename = repo_filename

    def tearDown(self):
        datapath = Path(h5database.config["datapath"])
        if datapath.is_dir():
            rmtree(datapath)

    def test_TableOfContent(self):
        """building toc"""
        self.assertTrue(os.path.isfile(self.repo_filename))
        with h5py.File(self.repo_filename, 'r') as h5:
            nfiles = len(list(h5.keys()))
            self.assertEqual(nfiles, self.n_test_files)

    def test_H5repo(self):
        datapath = Path(config["datapath"])
        tocfiles = list(datapath.rglob(f'*{config["toc_ext"]}'))
        tocfilename = tocfiles[0]
        self.o = H5repo(tocfilename, wrapperpy_class=H5TestClass)

        r_all = self.o.filter()
        self.assertEqual(len(r_all), 100)

        fan_cases = list()
        with h5py.File(self.o.toc_filename, 'r') as h5:
            for k in h5.keys():
                if h5[k].attrs['__db_file_type__'] == 'fan_case':
                    fan_cases.append(h5[k].file.filename)

        f = self.o.filter(Entry['/'].attrs['__db_file_type__'] == 'fan_case')
        self.assertEqual(len(f), len(fan_cases))

        count = 0
        f = self.o.filter(Entry['/operation_point/vfr'].attrs['mean'] < 0.001,
                          Entry['/'].attrs['__db_file_type__'] == 'fan_case')
        for fc in fan_cases:
            with h5py.File(fc, 'r') as h5:
                if h5['operation_point/vfr'].attrs['mean'] < 0.001:
                    count += 1
        self.assertEqual(len(f), count)

        r1 = self.o.filter(Entry['/'].attrs['operator'] == 'John')
        self.assertIsInstance(r1[:], list)
        with h5py.File(r1.toc_filename, 'r') as h5:
            for k in h5.keys():
                self.assertEqual(h5[k].attrs['operator'], 'John')

        r2 = self.o.filter(Entry['/operation_point/vfr'].attrs['mean'] > 0.001,
                           Entry['/operation_point/vfr'].attrs['mean'] < 0.01)
        count = 0
        for fc in fan_cases:
            with h5py.File(fc, 'r') as h5:
                if h5['operation_point/vfr'].attrs['mean'] < 0.01 and h5['operation_point/vfr'].attrs['mean'] > 0.001:
                    count += 1
        self.assertEqual(len(r2), count)

    def test_alternativeFilterRequest(self):
        tocfiles = glob.glob(os.path.join(config['datapath'],
                                          f'*{config["toc_ext"]}'))
        tocfilename = tocfiles[0]
        self.o = H5repo(tocfilename)
        _ = self.o.filter()
        _ = self.o.filter(Entry['/operation_point/vfr'].attrs['mean'] > 0,
                          Entry['/operation_point/vfr'].attrs['mean'] < 100)

    def test_03_preview(self):
        tocfiles = glob.glob(os.path.join(config['datapath'],
                                          f'*{config["toc_ext"]}'))
        tocfilename = tocfiles[0]
        self.o = H5repo(tocfilename)
        r = self.o.preview('operator', '/', 'attribute')
        self.assertIn('John', r)
        self.assertIn('Ellen', r)
        self.assertIn('Mike', r)
        self.assertIn('Susi', r)

    def test_filter2(self):
        datapath = Path(config["datapath"])
        tocfiles = list(datapath.rglob(f'*{config["toc_ext"]}'))
        tocfilename = tocfiles[0]
        repo = H5repo(tocfilename)
        _ = repo.filter(Entry['/'].exists(), Entry['operation_point/ptot'][-20:].mean() > 0,
                        Entry['/'].attrs['operator'] == 'John')
        _ = repo.filter(Entry['not'].exists())
        _ = repo.filter(Entry['not'].exists())
        _ = repo.filter(Entry['operation_point/ptot'].attrs['mean'].exists())

    def test_Entry(self):
        hdf_filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(hdf_filename, 'w') as h5:
            h5ds = h5.create_dataset('var', data=[1, 2, 3])
            h5ds.attrs['units'] = 'm/s'
            h5ds.attrs['a value'] = 13
            h5ds.attrs['a list'] = [1, 2, 3]
        with h5py.File(hdf_filename, 'r') as h5:
            ds = Dataset('var')
            self.assertFalse(ds.search(h5['/']))

            self.assertIsInstance(ds[0], Dataset)
            ds[0] == h5['var'][0]
            self.assertTrue(ds.search(h5))

            ds[0] == h5['var'][0]+1
            self.assertFalse(ds.search(h5))

            ds[0] > h5['var'][0]+1
            self.assertFalse(ds.search(h5))

            ds[0] >= h5['var'][0]+1
            self.assertFalse(ds.search(h5))

            ds[0] < h5['var'][0]+1
            self.assertTrue(ds.search(h5))

            ds[0] <= h5['var'][0]+1
            self.assertTrue(ds.search(h5))

            ds[:] == h5['var'][:]
            self.assertTrue(ds.search(h5))

            attr = Attr('/', 'units')
            self.assertTrue(attr.exists())
            self.assertEqual(attr._cmp_func, None)
            self.assertIsInstance(attr.__ge__(13), Attr)
            self.assertFalse(attr.search(h5))
            self.assertFalse(attr.search(h5['var']))
            self.assertIsInstance(attr.__gt__(13), Attr)
            self.assertIsInstance(attr.__le__(13), Attr)
            self.assertIsInstance(attr.__lt__(13), Attr)
            self.assertEqual(len(attr._cmp_func), 2)

            attr2 = Attr('/var', 'units')
            self.assertFalse(attr2.search(h5))
            self.assertIsInstance(attr2.__gt__(13), Attr)
            self.assertEqual(len(attr2._cmp_func), 2)
            with self.assertRaises(TypeError):
                self.assertFalse(attr2.search(h5))
            attr2.__eq__('m/s')
            self.assertTrue(attr2.search(h5))

            attr2[0:2].__eq__('m/')
            self.assertTrue(attr2.search(h5))

            attr3 = Attr('/var', 'a value')
            attr3.__eq__(13)
            self.assertTrue(attr3.search(h5))

            attr3 > 0
            self.assertTrue(attr3.search(h5))
            attr3 > 20
            self.assertFalse(attr3.search(h5))

            attr3 >= 0
            self.assertTrue(attr3.search(h5))
            attr3 >= 20
            self.assertFalse(attr3.search(h5))

            attr3 < 0
            self.assertFalse(attr3.search(h5))
            attr3 < 20
            self.assertTrue(attr3.search(h5))

            attr3 <= 0
            self.assertFalse(attr3.search(h5))
            attr3 <= 20
            self.assertTrue(attr3.search(h5))

            attr4 = Attr('/var', 'a list')
            attr4.__eq__(13)
            with self.assertRaises(ValueError):
                self.assertTrue(attr4.search(h5))
            attr4.mean() == 2
            self.assertTrue(attr4.search(h5))

            attr4 = Attr('/var', 'a list')
            attr4.std() == np.std(h5['var'].attrs['a list'])
            self.assertEqual(len(attr4._func_calls), 1)
            self.assertTrue(attr4.search(h5))
            self.assertEqual(len(attr4._func_calls), 1)

    def test_EntryManager(self):
        em = EntryManager()
        a = em.attrs
        self.assertIsInstance(a, AttributeManager)
