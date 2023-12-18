"""Test the mongoDB interface"""
import pathlib

import h5py
import types
import unittest
import warnings

from h5rdmtoolbox import use
from h5rdmtoolbox.database.lazy import LDataset
from h5rdmtoolbox.database.mongo import MongoDB

try:
    import pymongo

    PYMONGO_IS_INSTALLED = True
except ImportError:
    PYMONGO_IS_INSTALLED = False

try:
    client = pymongo.MongoClient(serverSelectionTimeoutMS=1.)
    client.server_info()
    SERVER_IS_RUNNING = True
except pymongo.errors.ServerSelectionTimeoutError as err:
    warnings.warn('Cannot test mongoDB features as no mongodb server is running!')
    SERVER_IS_RUNNING = False


def is_testable(func):
    """wrapper that checks if the function can be executed, which is only the case
    if the mongoDB is installed and a server is running"""

    def wrapper(*args, **kwargs):
        """wrapper"""
        if PYMONGO_IS_INSTALLED and SERVER_IS_RUNNING:
            return func(*args, **kwargs)
        else:
            return None

    return wrapper


class TestH5Mongo(unittest.TestCase):

    def setUp(self) -> None:
        """Create a database"""
        self.client = None
        self.collection = None

        if SERVER_IS_RUNNING and PYMONGO_IS_INSTALLED:
            self.client = pymongo.MongoClient()
            db = self.client.hdf_database_test
            self.collection = db.hdf_collection_test

        use(None)

    @is_testable
    def test_make_dict_mongo_compatible(self):
        import numpy as np
        from h5rdmtoolbox.database.mongo import make_dict_mongo_compatible
        self.assertEqual(make_dict_mongo_compatible({'a': 1}), {'a': 1})
        self.assertEqual(make_dict_mongo_compatible({'a': {'b': 4}}), {'a': {'b': 4}})
        self.assertEqual(make_dict_mongo_compatible({'a': None}), {'a': None})
        self.assertEqual(make_dict_mongo_compatible({'a': 4.1}),
                         {'a': 4.1})
        self.assertEqual(make_dict_mongo_compatible({'a': 4}),
                         {'a': 4})
        with self.assertWarns(UserWarning):
            self.assertEqual(make_dict_mongo_compatible({'a': np.array(5.5)}),
                             {'a': np.array(5.5)})

    @is_testable
    def test_insert(self):
        """Test the MongoDB class"""
        mongoDBInterface = MongoDB(collection=self.collection)

        with h5py.File('test.h5', 'w') as h5:
            h5.create_dataset('dataset', shape=(10, 20, 4))

            mongoDBInterface.insert_dataset(h5['dataset'], axis=None)

        self.assertEqual(1, mongoDBInterface.collection.count_documents({}))

        # We can call `find_one` on the collection ...
        res = mongoDBInterface.collection.find_one({'basename': 'dataset'})
        self.assertTrue('basename' in res)
        self.assertTrue('dataset' in res['basename'])

        # ... or we can call the `find_one` method of the interface:
        # the return type of calling `find_one` should be `LDataset`:
        self.assertIsInstance(
            mongoDBInterface.find_one({'basename': 'dataset'}),
            LDataset
        )
        self.assertIsInstance(mongoDBInterface.find({'basename': 'dataset'}),
                              types.GeneratorType)
        for r in mongoDBInterface.find({'basename': 'dataset'}):
            self.assertIsInstance(r, LDataset)

        # insert zero-th axis:
        self.client.drop_database('hdf_database_test')
        mongoDBInterface = MongoDB(collection=self.collection)
        with h5py.File('test.h5', 'w') as h5:
            h5.create_dataset('dataset', shape=(10, 20, 4))

            mongoDBInterface.insert_dataset(h5['dataset'], axis=0)
        self.assertEqual(10, mongoDBInterface.collection.count_documents({}))

        pathlib.Path('test.h5').unlink()

    @is_testable
    def test_find_one(self):

        mongoDBInterface = MongoDB(collection=self.collection)
        self.assertEqual(0, mongoDBInterface.collection.count_documents({}))

        with h5py.File('test.h5', 'w') as h5:
            h5.create_dataset('dataset', shape=(10, 20, 4))

            mongoDBInterface.insert_dataset(h5['dataset'], axis=0)

        self.assertEqual(10, mongoDBInterface.collection.count_documents({}))
        res = mongoDBInterface.find_one({'basename': 'dataset'})
        self.assertEqual(res[()].shape, (1, 20, 4))

    def tearDown(self) -> None:
        """Delete the database"""
        if self.client:
            # delete the database:
            self.client.drop_database('hdf_database_test')
