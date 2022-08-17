import pathlib
import unittest
from typing import List

import numpy as np
import pymongo.collection
from pymongo import MongoClient

import h5rdmtoolbox.h5database as h5db
from h5rdmtoolbox import H5File
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.h5database import mongo


def read_many_from_database(db_entry: pymongo.collection.Cursor) -> List[any]:
    with h5db.H5Files(*[entry['filename'] for entry in db_entry.rewind()]) as h5files:
        arrs = []
        for entry in db_entry.rewind():
            ds = h5files[pathlib.Path(entry['filename']).stem][entry['path']]

            _slice = [slice(*s) for s in entry['slice']]
            if _slice[0].stop - _slice[0].start == 1:
                _slice[0] = _slice[0].start
            arrs.append(ds[tuple(_slice)])
        return arrs


class TestH5Repo(unittest.TestCase):

    def setUp(self) -> None:
        client = MongoClient()

        db = client['synpiv_test_db']
        collection = db['test']

        self.collection = collection

    def test_insert_dataset(self):
        with H5File() as h5:
            h5.create_dataset('z', data=2, dtype=int,
                              units='', long_name='z_coordinate')
            h5.create_dataset('index', data=np.arange(0, 4, 1), dtype=int,
                              units='', long_name='index', make_scale=True)
            h5.create_dataset('images', data=np.random.random((4, 11, 21)),
                              units='counts',
                              long_name='a long name',
                              attach_scales=(h5['index'], None, None))
            h5['images'].attrs['COORDINATES'] = ['/z', ]

            h5.images.mongo.insert(axis=0, collection=self.collection)

        res = self.collection.find()
        for r in res:
            for k in ('filename', 'path', 'shape', 'ndim', 'slice', '/index', '/z', 'long_name', 'units'):
                self.assertIn(k, r.keys())

        # arr = read_many_from_database(res)
        # print(arr[0].plot())
        # import matplotlib.pyplot as plt
        # plt.show()

    def test_insert_group(self):
        with H5File() as h5:
            h5.attrs['rootatr'] = 1
            h5.attrs['str'] = 'test'

            h5.create_dataset('dataset', data=[1, 2, 3],
                              units='m/s', long_name='a velocity')

            g = h5.create_group('a_group')
            g.attrs['a'] = 1
            g.attrs['str'] = 'test'

            self.collection.drop()
            h5.mongo.insert(self.collection)

            res = self.collection.find()
            for r in res:
                print(r)
