import abc
from typing import Generator

import h5py

from .lazy import LHDFObject


class HDF5DBInterface(abc.ABC):
    """Abstract HDF5 Database interface. This intends to use the HDF5 file as a database.
    Subclasses, like `ExtHDF5DBInterface` implement interfaces to other databases and
    require other common methods. The most common methods across all implementations are
    `find_one` and `find` methods. They are abstract and need to be implemented by the
    concrete implementations.
    """

    @abc.abstractmethod
    def find_one(self, *args, **kwargs) -> LHDFObject:
        """Find one (the first) match based on a query argument(s).
        The arguments are not specified here, because they are
        implementation specific.
        """

    @abc.abstractmethod
    def find(self, *args, **kwargs) -> Generator[LHDFObject, None, None]:
        """Find all matches based on a query argument(s).
        The arguments are not specified here, because they are
        implementation specific.

        The reason for returning a Generator is that the results
        can be very large and the database content could change in
        the meantime. Thus, it is better to return a generator
        instead of a list.
        """


class ExtHDF5DBInterface(HDF5DBInterface):
    """This interface is abstract for those implementations sharing HDF5 data
    with other (external) databases, e.g. SQL or no SQL databases. One concrete implementation,
    for which this interface is intended, is the interface with mongoDB.

    Those implementations require `insert_dataset` and `insert_group` methods. Note, that this
    does open, whether the dataset is inserted with or without data (i.e. only metadata)!"""

    @abc.abstractmethod
    def insert_dataset(
            self,
            dataset: h5py.Dataset,
            *args,
            **kwargs):
        """insert dataset to database (may or may not include raw data)"""

    @abc.abstractmethod
    def insert_group(
            self,
            group: h5py.Group,
            *args,
            **kwargs):
        """insert group to database"""
