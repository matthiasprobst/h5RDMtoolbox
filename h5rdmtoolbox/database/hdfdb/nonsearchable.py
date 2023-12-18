
class NonInsertableDatabaseInterface:
    """A database interface that does not allow inserting datasets"""

    def insert_dataset(self, *args, **kwargs):
        """Insert a dataset. This is not possible for an HDF5 file."""
        raise NotImplementedError('By using an HDF5 file as a database, you cannot insert datasets')

    def insert_group(self, *args, **kwargs):
        """Insert a group. This is not possible for an HDF5 file."""
        raise NotImplementedError('By using an HDF5 file as a database, you cannot insert groups')
