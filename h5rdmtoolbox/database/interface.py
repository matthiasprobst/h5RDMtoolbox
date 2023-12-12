import abc
import h5py
from typing import Generator

from .lazy import LHDFObject


class HDF5DatabaseInterface(abc.ABC):
    """Abstract HDF5 Database interface.

    The init method is not abstract. Each database implementation
    needs to implement it on its own.

    The `insert` method covers the insertion of a dataset or group
    into the database. The `find_one` and `find` methods are used to
    query the database.
    """

    @abc.abstractmethod
    def insert_dataset(
            self,
            dataset: h5py.Dataset,
            *args,
            **kwargs):
        """insert dataset to database"""

    @abc.abstractmethod
    def insert_group(
            self,
            group: h5py.Group,
            *args,
            **kwargs):
        """insert group to database"""

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
