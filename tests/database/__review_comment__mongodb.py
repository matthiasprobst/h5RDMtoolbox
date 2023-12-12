import abc
import h5py
import pymongo.collection
from typing import Union

import h5rdmtoolbox as h5tbx

db = pymongo.Client()


class HDF5DatabaseInterface(abc.ABC):

    @abc.abstractmethod
    def insert(self, h5obj: Union[h5py.Dataset, h5py.Group], **kwargs):
        """insert dataset or group"""


class MongoDBInterface(HDF5DatabaseInterface):

    def __init__(self, collection: pymongo.collection.Collection):
        self.collection = collection

    def insert(self, h5obj, **kwargs):
        """Implementation already made..."""

    def find_one(self, *args, **kwargs):
        """call pymongo find_one implementation"""

    def find(self, *args, **kwargs):
        """call pymongo find implementation"""


class FileDBInterface(HDF5DatabaseInterface):

    def __init__(self):
        pass  # nothing to do here...

    def insert(self, filename, **kwargs):
        """Implementation already made..."""
        # only accept filename! OOOR somehow register the dataset and group names
        # maybe add it to the find query silently in the background and add
        # the filename at this point...

    def find_one(self, *args, **kwargs):
        """call pymongo find_one"""

    def find(self, *args, **kwargs):
        """call pymongo find"""


mongoCollection = MongoDBInterface(pymongo.MongoClient().my_collection)
hdfDB = FileDBInterface()

with h5tbx.File() as h5:
    mongoDB.insert(h5['dataset'])
    hdfDB.insert(h5['dataset'])

mongoDB.insert(fname1)
mongoDB.insert(fname2)
mongoDB.insert(fname3)

mongoDB.find({'....'})
