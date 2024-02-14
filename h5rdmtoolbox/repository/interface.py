import abc
from typing import List, Callable


class RepositoryInterface(abc.ABC):
    """Abstract base class for repository interfaces."""

    # __init__  must be implemented in the child class
    def __init__(self):
        raise RuntimeError('Not implemented.')

    @abc.abstractmethod
    def exists(self):
        """Check if the repository exists."""

    @property
    @abc.abstractmethod
    def metadata(self):
        """Get the metadata of the repository."""

    @metadata.setter
    @abc.abstractmethod
    def metadata(self, value):
        """Set the metadata of the repository."""

    @abc.abstractmethod
    def download_file(self, filename):
        """Download a specific file from the repository."""

    @abc.abstractmethod
    def download_files(self):
        """Download all files from the repository."""

    @abc.abstractmethod
    def get_filenames(self) -> List[str]:
        """Get a list of all filenames."""

    @abc.abstractmethod
    def upload_file(self, filename, overwrite: bool = False):
        """Upload a file to the repository."""

    def upload_hdf_file(self, filename, metamapper: Callable, overwrite: bool = False):
        """Upload an HDF5 file. Additionally a metadata file will be extracted from the
        HDF5 file using the metamapper function and is uploaded as well."""
        if metamapper:
            meta_data_file = metamapper(filename)
        self.upload_file(filename=filename, overwrite=overwrite)
        if metamapper:
            self.upload_file(filename=meta_data_file, overwrite=overwrite)

    @abc.abstractmethod
    def get_doi(self):
        """Get the DOI of the repository."""
