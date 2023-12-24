import json
import logging
import numpy as np
import pathlib
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.repository import h5metamapper

logger = logging.getLogger(__name__)


class TestMetadataMapper(unittest.TestCase):

    def test_hdf2json(self):
        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test'
            h5.create_dataset('test', data=1, attrs={'objtype': 'dataset'}, dtype='int32')
            json_filename = h5metamapper.hdf2json(file_or_filename=h5, json_filename=None)
        self.assertIsInstance(json_filename, pathlib.Path)
        self.assertTrue(json_filename.exists())
        self.assertEqual(json_filename.stem, h5.hdf_filename.stem)
        self.assertEqual(json_filename.parent, h5.hdf_filename.parent)
        self.assertEqual(json_filename.suffix, '.json')


        json_filename = h5metamapper.hdf2json(file_or_filename=h5.hdf_filename, json_filename=None)
        self.assertIsInstance(json_filename, pathlib.Path)
        self.assertTrue(json_filename.exists())
        self.assertEqual(json_filename.stem, h5.hdf_filename.stem)
        self.assertEqual(json_filename.parent, h5.hdf_filename.parent)
        self.assertEqual(json_filename.suffix, '.json')

        json_filename = h5metamapper.hdf2json(file_or_filename=h5.hdf_filename, json_filename='test.json')
        self.assertIsInstance(json_filename, pathlib.Path)
        self.assertTrue(json_filename.exists())
        with open(json_filename, 'r') as f:
            json_data = json.load(f)
        self.assertEqual(json_data['attrs']['title'], 'test')
        self.assertEqual(json_data['attrs']['__h5rdmtoolbox_version__'], h5tbx.__version__)
        self.assertEqual(json_data['test']['attrs']['objtype'], 'dataset')
        self.assertEqual(json_data['test']['props']['shape'], [])
        self.assertEqual(json_data['test']['props']['dtype'], 'int32')
        json_filename.unlink(missing_ok=True)

    def test_parse_dtype(self):
        self.assertEqual(h5metamapper._parse_dtype(np.array([1, 2, 3], dtype=np.int32)),
                         ['1', '2', '3'])
        self.assertEqual(h5metamapper._parse_dtype(np.array([1, 2, 3], dtype=np.int64)),
                         ['1', '2', '3'])

        class Dummy:
            def __str__(self):
                return 'dummy'

        d = Dummy()
        self.assertEqual(h5metamapper._parse_dtype(d), 'dummy')
        self.assertEqual(h5metamapper._parse_dtype(None), None)
        self.assertEqual(h5metamapper._parse_dtype(6), '6')
        self.assertEqual(h5metamapper._parse_dtype(6.54), '6.54')
        self.assertEqual(h5metamapper._parse_dtype('6.54'), '6.54')
