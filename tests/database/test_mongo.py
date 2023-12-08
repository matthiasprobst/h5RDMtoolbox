import datetime
import numpy as np
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox import tutorial
from h5rdmtoolbox import use

try:
    # noinspection PyUnresolvedReferences
    from h5rdmtoolbox.database import mongo
    import pymongo.collection
    from pymongo import MongoClient

    mongo_installed = True
except ImportError:
    mongo_installed = False
from h5rdmtoolbox.database.mongo import make_dict_mongo_compatible, type2mongo

if mongo_installed:
    class TestH5Mongo(unittest.TestCase):

        def setUp(self) -> None:
            use(None)
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

        def test_make_dict_mongo_compatible(self):
            self.assertDictEqual({'a': 4.3}, make_dict_mongo_compatible({'a': 4.3}))
            self.assertDictEqual({'a': 4}, make_dict_mongo_compatible({'a': 4}))
            self.assertDictEqual({'a': None}, make_dict_mongo_compatible({'a': None}))
            self.assertDictEqual({'a': {'b': 5.3}}, make_dict_mongo_compatible({'a': {'b': 5.3}}))
            self.assertDictEqual({'a': {'b': 6.3}}, make_dict_mongo_compatible({'a': {'b': float(6.3)}}))

        def test_type2mongo(self):
            self.assertEqual(None, type2mongo(None))
            self.assertEqual(4.3, type2mongo(float(4.3)))
            self.assertEqual([2.3], type2mongo(np.array([2.3])))
            self.assertEqual([5, ], type2mongo(np.array([5])))

        def test_insert_relative_filename(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    h5.mongo.insert(collection=self.collection)
                    self.assertEqual(self.collection.find_one({})['filename'], h5.filename)
                    self.collection.drop()
                with File() as h5:
                    h5.mongo.insert(collection=self.collection, use_relative_filename=True)
                    self.assertEqual(self.collection.find_one({})['filename'], h5.filename)

        def test_coordinates(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    h5.create_dataset('x', data=np.arange(0, 4, 1), dtype=int,
                                      attrs=dict(units='', long_name='x_coordinate'), make_scale=True)
                    h5.create_dataset('y', data=np.arange(0, 4, 1), dtype=int,
                                      attrs=dict(units='', long_name='y_coordinate'), make_scale=True)
                    h5.create_dataset('z', data=2, dtype=int,
                                      attrs=dict(units='', long_name='z_coordinate'))
                    h5.create_dataset('images', data=np.random.random((4, 4, 4)),
                                      attrs=dict(units='counts', long_name='a long name'),
                                      attach_scales=([h5['x'], h5['y']], None, None))
                    h5['images'].attrs['COORDINATES'] = ['/z', ]
                    h5.images.mongo.insert(collection=self.collection, axis=None)

        def test_insert_tree_structure(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    h5.create_dataset('ds_at_root', data=np.random.random((2, 10, 8)),
                                      attrs=dict(units='',
                                                 long_name='ds_at_root'))
                    g = h5.create_group('group1')
                    g.create_dataset('ds1', data=np.random.random((2, 10, 8)),
                                     attrs=dict(units='',
                                                long_name='ds_at_group1'))
                    g2 = g.create_group('group2')
                    g2.create_dataset('ds2', data=np.random.random((2, 10, 8)),
                                      attrs=dict(units='',
                                                 long_name='ds_at_group2'))
                    h5.mongo.insert(collection=self.collection, flatten_tree=False, recursive=True)
                    self.assertDictEqual(list(self.collection.find({}))[0]['group1'], {'ds1': {'shape': [2, 10, 8],
                                                                                               'ndim': 3,
                                                                                               'long_name': 'ds_at_group1',
                                                                                               'units': ''},
                                                                                       'group2': {
                                                                                           'ds2': {'shape': [2, 10, 8],
                                                                                                   'ndim': 3,
                                                                                                   'long_name': 'ds_at_group2',
                                                                                                   'units': ''}}})

        def test_tree_to_mongo(self):
            if self.mongodb_running:
                self.collection.drop()

                usernames = ('Allen', 'Mike', 'Ellen', 'Elliot')
                company = ('bikeCompany', 'shoeCompany', 'bikeCompany', 'shoeCompany')
                filenames = []
                for i, (username, company) in enumerate(zip(usernames, company)):
                    with File(h5tbx.utils.generate_temporary_filename(), 'w') as h5:
                        filenames.append(h5.hdf_filename)
                        h5.attrs['username'] = username
                        h5.attrs['company'] = company
                        h5.attrs['meta'] = {'day': 'monday', 'iday': 0}
                        h5.create_dataset('ds_at_root', data=np.random.random((2, 10, 8)),
                                          attrs=dict(units='',
                                                     long_name='ds_at_root'))
                        h5['ds_at_root'].make_scale()
                        g = h5.create_group('idgroup')
                        ds = g.create_dataset('ds_at_subgroup', data=np.random.random((2, 10, 13)),
                                              attrs=dict(units='',
                                                         long_name='ds_at_subgroup'))
                        ds.dims[0].attach_scale(h5['ds_at_root'])
                        ds.attrs['id'] = i

                with File(filenames[0]) as h5:
                    tree = h5.get_tree_structure(True)
                self.collection.insert_one(make_dict_mongo_compatible(tree))

        def test_insert_dataset(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    hdf_filename = h5.hdf_filename
                    h5.create_dataset('z', data=2, dtype=int,
                                      attrs=dict(units='', long_name='z_coordinate'))
                    h5.create_dataset('index', data=np.arange(0, 4, 1), dtype=int,
                                      attrs=dict(units='', long_name='index'), make_scale=True)
                    h5.create_dataset('index2', data=np.arange(0, 4, 1), dtype=int,
                                      attrs=dict(units='', long_name='index'), make_scale=True)
                    h5.create_dataset('index3', data=np.arange(0, 4, 1), dtype=int,
                                      attrs=dict(units='', long_name='index'), make_scale=False)
                    h5.create_dataset('images', data=np.random.random((4, 11, 21)),
                                      attrs=dict(units='counts', long_name='a long name'),
                                      attach_scales=([h5['index'], h5['index2']], None, None))
                    h5['images'].attrs['COORDINATES'] = ['/z', ]
                    h5['images'].attrs['None'] = None
                    h5.attrs['np_ndarray'] = np.array([1.2, -2.3])
                    h5['images'].attrs['np_ndarray'] = np.array([1.2, -2.3])
                    h5['images'].attrs['float'] = 1.2
                    h5['images'].attrs['np_float'] = np.float64(1.2)

                    h5.images.mongo.insert(axis=0, collection=self.collection)

                res = self.collection.find()

                now = datetime.datetime.utcnow()

                for r in res:
                    if r['name'] == 'images':
                        self.assertEqual(r['filename'], str(hdf_filename))
                        for k in (
                                'filename', 'path', 'shape', 'ndim', 'slice', 'index', 'index2', 'z', 'long_name',
                                'units'):
                            self.assertIn(k, r.keys())

                    self.assertTrue((now - r['file_creation_time']).total_seconds() < 1)

                self.collection.drop()
                with File(hdf_filename) as h5:
                    h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index'],))
                res = self.collection.find()
                for r in res:
                    self.assertIn('index', r.keys())
                    self.assertIn('index2', r.keys())
                    self.assertNotIn('index3', r.keys())

                self.collection.drop()
                with File(hdf_filename) as h5:
                    h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index'], h5['/index2']))
                res = self.collection.find()
                for r in res:
                    self.assertIn('index', r.keys())
                    self.assertIn('index2', r.keys())
                    self.assertNotIn('index3', r.keys())

                self.collection.drop()
                with File(hdf_filename) as h5:
                    h5.images.mongo.insert(axis=0, collection=self.collection, dims=(h5['/index3'],))
                res = self.collection.find()
                for r in res:
                    self.assertIn('index', r.keys())
                    self.assertIn('index2', r.keys())
                    self.assertIn('index3', r.keys())

        def test_insert_dataset_update(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    hdf_filename = h5.hdf_filename
                    h5.create_dataset('z', data=2, dtype=int,
                                      attrs=dict(units='', long_name='z_coordinate'))
                    for i in range(3):
                        h5.z.mongo.insert(axis=None, collection=self.collection, update=True)
                    self.assertEqual(self.collection.count_documents({}), 1)
                    for i in range(3):
                        h5.z.mongo.insert(axis=None, collection=self.collection, update=False)
                    self.assertEqual(self.collection.count_documents({}), 4)
                    for r in self.collection.find({}):
                        self.assertEqual(r['filename'], str(h5.hdf_filename))
                        self.assertEqual(r['name'], '/z')

        def test_insert_group(self):
            if self.mongodb_running:
                self.collection.drop()
                with File() as h5:
                    h5.attrs['rootatr'] = 1
                    h5.attrs['str'] = 'test'

                    h5.create_dataset('dataset', data=[1, 2, 3],
                                      attrs=dict(units='m/s', long_name='a velocity'))

                    g = h5.create_group('a_group')
                    g.attrs['a'] = 1
                    g.attrs['str'] = 'test'

                    self.collection.drop()
                    h5.mongo.insert(self.collection)

                    self.assertEqual(self.collection.count_documents({}), 2)
                    now = datetime.datetime.now()
                    for r in self.collection.find({}):
                        self.assertTrue((now - r['file_creation_time']).total_seconds() < 1)

        def test_insert_group_flatten(self):
            if self.mongodb_running:
                self.collection.drop()

                repo_filenames = tutorial.Database.generate_test_files()
                for fname in repo_filenames:
                    with File(fname) as h5:
                        h5.mongo.insert(collection=self.collection, recursive=True, flatten_tree=True)
                now = datetime.datetime.now() - datetime.timedelta(minutes=1)
                for r in self.collection.find({}):
                    self.assertTrue((now - r['file_creation_time']).total_seconds() < 20)
