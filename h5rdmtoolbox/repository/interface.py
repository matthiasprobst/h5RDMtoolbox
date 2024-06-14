import abc
import pathlib
import warnings
from typing import Callable, Iterable, Union


def _HDF2JSON(filename: Union[str, pathlib.Path]) -> pathlib.Path:
    """The default metamapper function for HDF5 files. It extracts metadata from the HDF5 file
    and stores it in a JSON-LD file. The filename of the metadata file is returned.

    Parameter
    --------
    filename: Union[str, pathlib.Path]
        The filename of the HDF5 file.

    Return
    ------
    pathlib.Path
        The filename of the metadata file (.json).

    Raises
    ------
    ValueError
        If the filename does not have the correct suffix.

    """
    if pathlib.Path(filename).suffix not in ('.hdf', '.hdf5', '.h5'):
        raise ValueError('The (default) HDF2JSON metamapper function can only be used with HDF5 files.')

    from ..wrapper.jsonld import hdf2jsonld

    return hdf2jsonld(filename=filename, skipND=1)


class RepositoryInterface(abc.ABC):
    """Abstract base class for repository interfaces."""

    # __init__  must be implemented in the child class
    def __init__(self):
        raise RuntimeError('Not implemented.')

    @abc.abstractmethod
    def exists(self):
        """Check if the repository exists."""

    @abc.abstractmethod
    def get_metadata(self):
        """Get the metadata of the repository."""

    @abc.abstractmethod
    def set_metadata(self, value):
        """Set the metadata of the repository."""

    @abc.abstractmethod
    def download_file(self, filename):
        """Download a specific file from the repository."""

    @abc.abstractmethod
    def download_files(self):
        """Download all files from the repository."""

    @abc.abstractmethod
    def get_filenames(self) -> Iterable:
        """Get a list of all filenames."""

    @abc.abstractmethod
    def _upload_file(self, filename: Union[str, pathlib.Path], overwrite: bool = False):
        """Upload a file to the repository. This is a regular file uploader, hence the
        file can be of any type. This is a private method, which needs to be implemented
        by every repository interface. Will be called by `upload_file`"""

    def upload_file(self,
                    filename: Union[str, pathlib.Path],
                    metamapper: Union[None, Callable[[Union[str, pathlib.Path]], pathlib.Path]] = _HDF2JSON,
                    overwrite: bool = False):
        """Upload a file to the repository. A metamapper function can be provided optionally. It
        extracts metadata from the target file and also uploads it to the repository. This feature is especially
        useful for large files and especially for HDF5 files. Although the method call is very basic and does not
        further specify the metamapper function behaviour, the intended output (meta) file should be a JSON-LD
        file for the sake of interoperability. Ultimately, the metadata file should be downloaded first by the user
        interested in the repository data, in order to understand the file content. This avoids downloading a very
        large file, which might not be needed.

        Implementation details/requirements for the metamapper function:
        - Takes only one argument, which is the filename (as str or pathlib.Path) of the target file
        - Must return the filename of the metadata file

        Parameter
        --------
        filename: Union[str, pathlib.Path]
            The filename of the file to be uploaded.
        metamapper: Union[None, Callable[[Union[str, pathlib.Path]], pathlib.Path]]
            A function that extracts metadata from the target file and stores it in a file. The filename of the
            metadata file is returned by the function. If None, no metadata is extracted.
        overwrite: bool=False
            If True, the file will be overwritten if it already exists in the repository. If False, an error
            will be raised if the file already exists.

        """
        if not pathlib.Path(filename).exists():
            raise FileNotFoundError(f'The file {filename} does not exist.')

        if metamapper:
            meta_data_file = metamapper(filename)
        self._upload_file(filename=filename, overwrite=overwrite)
        if metamapper:
            self._upload_file(filename=meta_data_file, overwrite=overwrite)

    def upload_hdf_file(self,
                        filename,
                        metamapper: Callable[[Union[str, pathlib.Path]], pathlib.Path],
                        overwrite: bool = False):
        """Upload an HDF5 file. Additionally, a metadata file will be extracted from the
        HDF5 file using the metamapper function and is uploaded as well.
        The metamapper function takes a filename, extracts the metadata and stores it in
        a file. The filename of it is returned by the function. It is automatically uploaded
        with the HDF5 file."""
        warnings.warn('This method is deprecated. Use `upload_file` instead and provide the '
                      'metamapper parameter there', DeprecationWarning)
        return self.upload_file(filename, metamapper, overwrite)

    @abc.abstractmethod
    def get_doi(self):
        """Get the DOI of the repository."""
