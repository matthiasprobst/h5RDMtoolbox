import datetime
import pathlib
import unittest
from typing import List

import numpy as np
import pymongo.collection
from pymongo import MongoClient

import h5rdmtoolbox as h5tbx
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

    def test_tree_to_mongo(self):
        from h5rdmtoolbox.h5database.mongo import make_dict_mongo_compatible
        self.collection.drop()

        usernames = ('Allen', 'Mike', 'Ellen', 'Alliot')
        company = ('bikeCompany', 'shoeCompany', 'bikeCompany', 'shoeCompany')
        filenames = []
        for i, (username, company) in enumerate(zip(usernames, company)):
            with h5tbx.H5File(h5tbx.generate_temporary_filename(), 'w') as h5:
                filenames.append(h5.hdf_filename)
                h5.attrs['username'] = username
                h5.attrs['company'] = company
                h5.attrs['meta'] = {'day': 'monday', 'iday': 0}
                g = h5.create_group('idgroup')
                g.attrs['id'] = i

        with h5tbx.H5File(filenames[0]) as h5:
            tree = h5.get_tree_structure(True)
        self.collection.insert_one(make_dict_mongo_compatible(tree))

    def test_insert_dataset(self):
        self.collection.drop()
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

        now = datetime.datetime.utcnow()

        for r in res:
            for k in ('filename', 'path', 'shape', 'ndim', 'slice', 'index', 'z', 'long_name', 'units'):
                self.assertIn(k, r.keys())

            self.assertTrue((now - r['file_creation_time']).total_seconds() < 0.1)
            self.assertTrue((now - r['document_last_modified']).total_seconds() < 0.1)

        # arr = read_many_from_database(res)
        # print(arr[0].plot())
        # import matplotlib.pyplot as plt
        # plt.show()

    def test_insert_group(self):
        self.collection.drop()
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

            self.assertEqual(self.collection.count_documents({}), 2)
            now = datetime.datetime.utcnow()
            for r in self.collection.find({}):
                self.assertTrue((now - r['file_creation_time']).total_seconds() < 0.1)
                self.assertTrue((now - r['document_last_modified']).total_seconds() < 0.1)

    def test_insert_group2(self):
        self.collection.drop()
        import h5rdmtoolbox as h5tbx
        from h5rdmtoolbox import tutorial

        repo_filenames = tutorial.Database.generate_test_files()
        for fname in repo_filenames:
            with h5tbx.H5File(fname) as h5:
                h5.mongo.insert(collection=self.collection, recursive=True)
        now = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        for r in self.collection.find({}):
            self.assertTrue((now - r['file_creation_time']).total_seconds() < 20)
            self.assertTrue((now - r['document_last_modified']).total_seconds() < 20)
