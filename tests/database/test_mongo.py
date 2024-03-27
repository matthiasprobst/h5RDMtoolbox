"""Test the mongoDB interface"""
import h5py
import numpy as np
import pathlib
import types
import unittest
import warnings
from datetime import datetime
from skimage.feature import graycomatrix, graycoprops
from sklearn.datasets import load_digits  # ! pip install scikit-learn

import h5rdmtoolbox as h5tbx
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

    def test_type2mongo(self):
        from h5rdmtoolbox.database.mongo import type2mongo
        self.assertEqual(type2mongo(1), 1)
        self.assertEqual(type2mongo(1.1), 1.1)
        self.assertEqual(type2mongo('a'), 'a')
        self.assertEqual(type2mongo(None), None)
        self.assertEqual(type2mongo({'a': 1}), {'a': 1})
        self.assertEqual(type2mongo([1, 2, 3]), [1, 2, 3])
        self.assertEqual(type2mongo({'a': [1, 2, 3]}), {'a': [1, 2, 3]})
        self.assertEqual(type2mongo({'a': {'b': 4}}), {'a': {'b': 4}})
        self.assertEqual(type2mongo({'a': None}), {'a': None})
        self.assertEqual(type2mongo({'a': 4.1}), {'a': 4.1})
        self.assertEqual(type2mongo(np.array([1, 2, 3])), [1, 2, 3])
        self.assertEqual(type2mongo(np.array(1, dtype=np.int32)), 1)
        self.assertEqual(type2mongo(np.array(1, dtype=np.float32)), 1.0)
        self.assertEqual(type2mongo(np.array(1, dtype='S1')), b'1')
        now = datetime.now()
        self.assertEqual(type2mongo(now), now)

        class MyClass:
            """MyClass"""

            def __str__(self):
                return 'MyClass'

        self.assertEqual(type2mongo(MyClass()), 'MyClass')

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
            h5.create_dataset('dataset0d', data=1)
            h5.create_dataset('dataset', shape=(10, 20, 4))

            mongoDBInterface.insert_dataset(h5['dataset0d'], axis=None)
            mongoDBInterface.insert_dataset(h5['dataset'], axis=None)

        self.assertEqual(2, mongoDBInterface.collection.count_documents({}))

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

    @is_testable
    def test_sklearn_digits(self):
        digits = load_digits()

        filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')

        with h5tbx.File(filename, 'w') as h5:
            ds_trg = h5.create_dataset('digit',
                                       data=digits.target,
                                       make_scale=True)
            ds_img = h5.create_dataset('images',
                                       shape=(len(digits.images), 8, 8))

            ds_mean = h5.create_dataset('mean',
                                        shape=(len(digits.images),),
                                        make_scale=True)
            ds_diss = h5.create_dataset('dissimilarity',
                                        shape=(len(digits.images),),
                                        make_scale=True)
            ds_corr = h5.create_dataset('correlation',
                                        shape=(len(digits.images),),
                                        make_scale=True)

            for i, img in enumerate(digits.images):
                ds_img[i, :, :] = img
                ds_mean[i] = np.mean(img)

                glcm = graycomatrix(img.astype(int), distances=[5], angles=[0], levels=256,
                                    symmetric=True, normed=True)
                ds_diss[i] = graycoprops(glcm, 'dissimilarity')[0, 0]
                ds_corr[i] = graycoprops(glcm, 'correlation')[0, 0]

            ds_img.dims[0].attach_scale(ds_trg)
            ds_img.dims[0].attach_scale(ds_mean)
            ds_img.dims[0].attach_scale(ds_diss)
            ds_img.dims[0].attach_scale(ds_corr)

        mdb = MongoDB(collection=self.collection)
        mdb.collection.drop()  # clean the collection just to be certain that it is really empty

        with h5tbx.File(filename) as h5:
            mdb.insert_dataset(h5['images'], axis=None)

        self.assertEqual(self.collection.count_documents({}), 1)
        res = mdb.find_one({})
        self.assertEqual(res[()].shape, (len(digits.images), 8, 8))

        # second option:
        mdb.collection.drop()
        with h5tbx.File(filename) as h5:
            mdb.insert_dataset(h5['images'], axis=0, update=False)
        self.assertEqual(self.collection.count_documents({}), len(digits.images))
        one_res = mdb.find_one({'digit': {'$eq': 3}})
        self.assertEqual(one_res[()].shape, (1, 8, 8))

    def tearDown(self) -> None:
        """Delete the database"""
        if self.client:
            # delete the database:
            self.client.drop_database('hdf_database_test')
