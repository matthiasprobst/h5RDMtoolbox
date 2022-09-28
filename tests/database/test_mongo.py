import datetime
import pathlib
import unittest
import warnings
from typing import List

import numpy as np
import pymongo.collection
from pymongo import MongoClient

import h5rdmtoolbox as h5tbx
import h5rdmtoolbox.database as h5db
from h5rdmtoolbox import H5File
from h5rdmtoolbox import tutorial
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.database import mongo
from h5rdmtoolbox.database.mongo import make_dict_mongo_compatible


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


class TestH5Mongo(unittest.TestCase):

    def setUp(self) -> None:
        self.mongodb_running = True
        try:
            client = MongoClient(serverSelectionTimeoutMS=1.)
            client.server_info()
            mongodb_av = True
        except pymongo.errors.ServerSelectionTimeoutError as err:
            mongodb_av = False
            warnings.warn('Cannot test mongoDB features as no mongodb server is running!')

        if mongodb_av:
            db = client['h5tbx_test_db']
            collection = db['test']
            self.collection = collection
        else:
            self.mongodb_running = False

    def test_tree_to_mongo(self):
        if self.mongodb_running:
            self.collection.drop()

            usernames = ('Allen', 'Mike', 'Ellen', 'Elliot')
            company = ('bikeCompany', 'shoeCompany', 'bikeCompany', 'shoeCompany')
            filenames = []
            for i, (username, company) in enumerate(zip(usernames, company)):
                with h5tbx.H5File(h5tbx.generate_temporary_filename(), 'w') as h5:
                    filenames.append(h5.hdf_filename)
                    h5.attrs['username'] = username
                    h5.attrs['company'] = company
                    h5.attrs['meta'] = {'day': 'monday', 'iday': 0}
                    h5.create_dataset('ds_at_root', data=np.random.random((2, 10, 8)), units='',
                                      long_name='ds_at_root')
                    h5['ds_at_root'].make_scale()
                    g = h5.create_group('idgroup')
                    ds = g.create_dataset('ds_at_subgroup', data=np.random.random((2, 10, 13)), units='',
                                          long_name='ds_at_subgroup')
                    ds.dims[0].attach_scale(h5['ds_at_root'])
                    ds.attrs['id'] = i

            with h5tbx.H5File(filenames[0]) as h5:
                tree = h5.get_tree_structure(True)
            self.collection.insert_one(mongo.make_dict_mongo_compatible(tree))

    def test_insert_dataset(self):
        if self.mongodb_running:
            self.collection.drop()
            with H5File() as h5:
                hdf_filename = h5.hdf_filename
                h5.create_dataset('z', data=2, dtype=int,
                                  units='', long_name='z_coordinate')
                h5.create_dataset('index', data=np.arange(0, 4, 1), dtype=int,
                                  units='', long_name='index', make_scale=True)
                h5.create_dataset('index2', data=np.arange(0, 4, 1), dtype=int,
                                  units='', standard_name='standard_index', make_scale=True)
                h5.create_dataset('index3', data=np.arange(0, 4, 1), dtype=int,
                                  units='', long_name='index', make_scale=False)
                h5.create_dataset('images', data=np.random.random((4, 11, 21)),
                                  units='counts',
                                  long_name='a long name',
                                  attach_scales=([h5['index'], h5['index2']], None, None))
                h5['images'].attrs['COORDINATES'] = ['/z', ]

                h5.images.mongo.insert(axis=0, collection=self.collection, use_standard_names_for_dimscales=True)

            res = self.collection.find()
            self.assertTrue('standard_index' in self.collection.find_one())

            now = datetime.datetime.utcnow()

            for r in res:
                if r['name'] == 'images':
                    self.assertEqual(r['filename'], str(hdf_filename))
                    for k in (
                            'filename', 'path', 'shape', 'ndim', 'slice', 'index', 'index2', 'z', 'long_name', 'units'):
                        self.assertIn(k, r.keys())

                self.assertTrue((now - r['file_creation_time']).total_seconds() < 0.1)

            self.collection.drop()
            with H5File(hdf_filename) as h5:
                h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index'],))
            res = self.collection.find()
            for r in res:
                self.assertIn('index', r.keys())
                self.assertIn('index2', r.keys())
                self.assertNotIn('index3', r.keys())

            self.collection.drop()
            with H5File(hdf_filename) as h5:
                h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index'], h5['/index2']))
            res = self.collection.find()
            for r in res:
                self.assertIn('index', r.keys())
                self.assertIn('index2', r.keys())
                self.assertNotIn('index3', r.keys())

            self.collection.drop()
            with H5File(hdf_filename) as h5:
                h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index3'],))
            res = self.collection.find()
            for r in res:
                self.assertIn('index', r.keys())
                self.assertIn('index2', r.keys())
                self.assertIn('index3', r.keys())

    def test_insert_dataset_update(self):
        if self.mongodb_running:
            self.collection.drop()
            with H5File() as h5:
                hdf_filename = h5.hdf_filename
                h5.create_dataset('z', data=2, dtype=int,
                                  units='', long_name='z_coordinate')
                for i in range(3):
                    h5.z.mongo.insert(axis=None, collection=self.collection, update=True)
                self.assertEqual(self.collection.count_documents({}), 1)
                for i in range(3):
                    h5.z.mongo.insert(axis=None, collection=self.collection, update=False)
                self.assertEqual(self.collection.count_documents({}), 4)
                for r in self.collection.find({}):
                    print(r)

    def test_insert_group(self):
        if self.mongodb_running:
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
                    self.assertTrue((now - r['file_creation_time']).total_seconds() < 1)

    def test_insert_group_flatten(self):
        if self.mongodb_running:
            self.collection.drop()

            repo_filenames = tutorial.Database.generate_test_files()
            for fname in repo_filenames:
                with h5tbx.H5File(fname) as h5:
                    h5.mongo.insert(collection=self.collection, recursive=True, flatten_tree=True)
            now = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
            for r in self.collection.find({}):
                self.assertTrue((now - r['file_creation_time']).total_seconds() < 20)

    def test_found(self):
        with h5tbx.H5File() as h5:
            g = h5.create_group('/grp/subgrp/name1')
            ds1 = h5.create_dataset('ds1', shape=(10, 2), units='', long_name='long1')
            ds2 = h5.create_dataset('ds2', shape=(10, 2), units='', long_name='long1')
            dsg2 = h5.create_group('g2', long_name='long1')
            g.attrs['testuser'] = 'me'
            g.attrs['num'] = 10.2
            h5.attrs['num'] = .2

            self.assertEqual([ds1, ], h5.find({'long_name': 'long1', '$basename': 'ds1'}))
            self.assertEqual([h5['ds2'], h5['ds1']],
                             h5.find({'long_name': 'long1'}, objfilter='dataset'))
            self.assertEqual([h5['g2']],
                             h5.find({'long_name': 'long1'}, objfilter='group'))

            self.assertEqual(h5.find_one({'$name': '/grp/subgrp'}), h5['/grp/subgrp/'])
            self.assertEqual(h5.find_one({'num': {'$lte': .2}}), h5)
            #
            self.assertEqual(h5.find({'testuser': 'me2'}), [])
            self.assertEqual(h5.find({'testuser': 'me'}), [g])
            self.assertEqual(h5.find({'$name': '/grp/subgrp'}), [h5['/grp/subgrp/'], ])
