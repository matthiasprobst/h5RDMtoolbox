import datetime
import pathlib
import time
import unittest

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.utils import DownloadFileManager

__this_dir__ = pathlib.Path(__file__).parent


class TestUtils(unittest.TestCase):

    def test_hash(self):
        with h5tbx.File() as h5:
            pass
        self.assertEqual(h5tbx.get_checksum(h5.hdf_filename),
                         '6781e0baec8d65b9a95a3e879a5098d1')

    def test_touch_tmp_hdf5_file(self):
        with h5tbx.set_config(auto_create_h5tbx_version=False):
            now = datetime.datetime.now()
            tmp_hdf5file = h5tbx.utils.touch_tmp_hdf5_file(touch=True,
                                                           attrs={'dtime': now})
            self.assertTrue(h5tbx.UserDir['tmp'] in tmp_hdf5file.parents)
            self.assertEqual(h5tbx.utils.get_filesize(tmp_hdf5file).magnitude, 6144)
            self.assertEqual(h5tbx.get_filesize(tmp_hdf5file).magnitude, 6144)
            self.assertEqual(h5tbx.utils.get_filesize(tmp_hdf5file).units, h5tbx.get_ureg().Unit('byte'))

    def test_remove_special_chars(self):
        self.assertEqual('test123_', h5tbx.utils.remove_special_chars('test123&%$#_'))
        self.assertEqual('test123', h5tbx.utils.remove_special_chars('test123&%$#_', keep_special=''))
        self.assertEqual('test123&', h5tbx.utils.remove_special_chars('test123&%$#_', keep_special='&'))

    def test_generate_temporary_filename(self):
        f = h5tbx.utils.generate_temporary_filename(touch=True)
        self.assertTrue(f.exists())
        f = h5tbx.utils.generate_temporary_filename(touch=False)
        self.assertFalse(f.exists())

        next_n = next(h5tbx.user._filecounter)
        f_block = h5tbx.user.UserDir['tmp'] / f'test{next_n + 1}.txt'
        f_predict = h5tbx.user.UserDir['tmp'] / f'test{next_n + 2}.txt'
        with open(f_block, 'w') as f:
            pass

        fnew = h5tbx.utils.generate_temporary_filename(touch=True, prefix='test', suffix='.txt')
        self.assertTrue(fnew.exists())
        self.assertTrue(fnew.is_file())
        self.assertEqual(f_predict, fnew)

    def test_generate_temporary_directory(self):
        import shutil
        from h5rdmtoolbox.user import _dircounter

        shutil.rmtree(str(h5tbx.user.UserDir['tmp']))
        n = next(_dircounter) + 1
        testfolder = h5tbx.utils.generate_temporary_directory(prefix='testfolder')
        folder = h5tbx.user.UserDir['tmp'] / f'testfolder{n + 1}'
        folder.mkdir()
        testfolder = h5tbx.utils.generate_temporary_directory(prefix='testfolder')
        self.assertTrue(testfolder.exists())
        self.assertTrue(testfolder.is_dir())
        self.assertEqual(h5tbx.user.UserDir['tmp'] / f'testfolder{n + 2}', testfolder)

    def test_create_special_attribute(self):
        with h5tbx.File() as h5:
            h5tbx.utils.create_special_attribute(h5.attrs, 'test', h5tbx.user.UserDir['tmp'])
            self.assertEqual(str(h5tbx.user.UserDir['tmp']), h5.attrs['test'])
            h5tbx.utils.create_special_attribute(h5.attrs, 'test', None)
            self.assertEqual('None', h5.attrs['test'])

    def test_process_obj_filter_input(self):
        self.assertEqual(None, h5tbx.utils.process_obj_filter_input(None))
        self.assertEqual(h5py.Dataset, h5tbx.utils.process_obj_filter_input('dataset'))
        with self.assertRaises(ValueError):
            h5tbx.utils.process_obj_filter_input('invalid')
        with self.assertRaises(TypeError):
            h5tbx.utils.process_obj_filter_input(h5tbx.File)

    def test_DocStringParser(self):
        def _test():
            """test"""
            pass

        dsp = h5tbx.utils.DocStringParser(_test)
        self.assertEqual('test', dsp.get_original_doc_string())
        self.assertEqual((None, [], [], []), h5tbx.utils.DocStringParser.parse_docstring(dsp.get_original_doc_string()))
        self.assertEqual((None, [], [], []), h5tbx.utils.DocStringParser.parse_docstring(''))

    def test_has_datasets(self):
        with h5tbx.use(None):
            with h5tbx.set_config(auto_create_h5tbx_version=False):
                with h5tbx.File() as h5:
                    self.assertFalse(h5tbx.utils.has_datasets(h5))
                    h5.create_dataset('test', data=1)
                    self.assertTrue(h5tbx.utils.has_datasets(h5))
                    self.assertFalse(h5tbx.utils.has_groups(h5))
                    h5.create_group('testgroup')
                    self.assertTrue(h5tbx.utils.has_groups(h5))

                self.assertTrue(h5tbx.utils.has_datasets(h5.hdf_filename))
                self.assertTrue(h5tbx.utils.has_groups(h5.hdf_filename))

    def test_download_manager(self):
        dfm = DownloadFileManager()
        self.assertTrue(dfm.file_directory.exists())

        dfm2 = DownloadFileManager()
        self.assertTrue(dfm is dfm2)  # is a singleton!

        dfm.reset_registry()
        self.assertFalse('e678a1eca79d5a836b58772eeee7f831' in dfm.registry)
        self.assertEqual(0, len(dfm))

        time_st = time.time_ns()
        downloaded_filename = dfm.download("https://zenodo.org/records/10428808/files/planar_piv.yaml?download=1",
                                           checksum='e678a1eca79d5a836b58772eeee7f831')
        time1 = time.time_ns() - time_st
        self.assertTrue(downloaded_filename.exists())
        self.assertTrue('e678a1eca79d5a836b58772eeee7f831' in dfm.registry)

        self.assertTrue(downloaded_filename.name, 'planar_piv.yaml=download=1')
        self.assertEqual(1, len(dfm))
        
        downloaded_filename = dfm.download("https://zenodo.org/records/10428808/files/planar_piv.yaml?download=1",
                                           checksum='e678a1eca79d5a836b58772eeee7f831')

        self.assertTrue(downloaded_filename.exists())
        self.assertTrue(downloaded_filename.name, 'planar_piv.yaml=download=1')

        dfm.reset_registry()
        self.assertFalse('e678a1eca79d5a836b58772eeee7f831' in dfm.registry)
        self.assertEqual(0, len(dfm))

        h5tbx.utils.download_file("https://zenodo.org/records/10428808/files/planar_piv.yaml?download=1",
                                  checksum='e678a1eca79d5a836b58772eeee7f831')

        self.assertTrue('e678a1eca79d5a836b58772eeee7f831' in dfm.registry)
        time_st = time.time_ns()
        h5tbx.utils.download_file("https://zenodo.org/records/10428808/files/planar_piv.yaml?download=1",
                                  checksum='e678a1eca79d5a836b58772eeee7f831')
