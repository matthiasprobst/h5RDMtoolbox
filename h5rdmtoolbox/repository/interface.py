import abc
import logging
import pathlib
import warnings
from typing import Callable, Union, Optional, List, Dict

from h5rdmtoolbox.utils import deprecated

logger = logging.getLogger('h5rdmtoolbox')


def _HDF2JSON(filename: Union[str, pathlib.Path], **kwargs) -> pathlib.Path:
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

    from h5rdmtoolbox.ld import hdf2jsonld

    return hdf2jsonld(filename=filename, skipND=1)


class RepositoryFile:
    """The interface class to files in a repository"""

    def __init__(self,
                 identifier,
                 identifier_url,
                 download_url,
                 access_url,
                 checksum,
                 name,
                 size,
                 media_type,
                 access_token=None,
                 **kwargs):
        self.download_url = download_url
        self.access_url = access_url
        self.checksum = checksum
        self.name = name
        self.media_type = media_type
        self.size = size
        self.identifier = identifier
        self.identifier_url = identifier_url
        self.access_token = access_token
        self.additional_data = kwargs

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"

    def info(self) -> Dict:
        return dict(identifier=self.identifier,
                    identifier_url=self.identifier_url,
                    download_url=self.download_url,
                    access_url=self.access_url,
                    media_type=self.media_type,
                    checksum=self.checksum,
                    filename=self.filename,
                    size=self.size)

    def jsonld(self) -> str:
        """Returns the JSONLD representation of the file"""
        jsonld_str = f"""{{
    "@context": {{
        "schema": "https://schema.org",
        "dcat": "http://www.w3.org/ns/dcat#",
        "spdx": "http://spdx.org/rdf/terms#"
    }},
    "@id": "{self.identifier_url}",
    "@type": "dcat:Distribution"
    "schema:identifier": "{self.identifier}",
"""

        if self.size:
            jsonld_str += f',\n    "dcat:byteSize": "{self.size}"'
        if self.access_url:
            jsonld_str += f',\n    "dcat:accessURL": "{self.access_url}"'
        if self.download_url:
            jsonld_str += f',\n    "dcat:downloadURL": "{self.download_url}"'
        if self.checksum:
            jsonld_str += f',\n    "spdx:checksum": "{self.checksum}"'
        if self.media_type:
            jsonld_str += f',\n    "dcat:mediaType": "{self.media_type}"'
        jsonld_str += '\n}'
        return jsonld_str

    @property
    def suffix(self) -> str:
        return pathlib.Path(self.name).suffix

    def download(self, target_folder: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
        """Download the file to target_folder. If None, local user dir is used.
        Returns the file location"""
        from .utils import download_file
        return download_file(file_url=self.download_url,
                             target_folder=target_folder,
                             access_token=self.access_token)


class RepositoryInterface(abc.ABC):
    """Abstract base class for repository interfaces."""

    # __init__  must be implemented in the child class
    def __init__(self):
        raise RuntimeError('Not implemented.')

    @property
    @abc.abstractmethod
    def identifier(self) -> str:
        """Return the identifier of the Repository."""

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Return the title of the Repository."""
        
    @abc.abstractmethod
    def exists(self):
        """Check if the repository exists."""

    @abc.abstractmethod
    def get_metadata(self):
        """Get the metadata of the repository."""

    @abc.abstractmethod
    def set_metadata(self, metadata):
        """Set the metadata of the repository."""

    @abc.abstractmethod
    def download_file(self, filename):
        """Download a specific file from the repository.

        ..note: This method is deprecated. Use method `.files.get(filename).download()` method instead.
        """

    @abc.abstractmethod
    def download_files(self):
        """Download all files from the repository.

        ..note: This method is deprecated. Please iterate over `files` and call .download() on the items.
        """

    @deprecated(version='1.4.0rc1',
                msg='Please use `list(self.files.keys())` instead')
    def get_filenames(self) -> List[str]:
        """Get a list of all filenames."""
        return list(self.files.keys())

    @property
    @abc.abstractmethod
    def files(self) -> Dict[str, RepositoryFile]:
        """List of all files in the repository."""

    @abc.abstractmethod
    def __upload_file__(self, filename: Union[str, pathlib.Path], overwrite: bool = False):
        """Upload a file to the repository. This is a regular file uploader, hence the
        file can be of any type. This is a private method, which needs to be implemented
        by every repository interface. Will be called by `upload_file`"""

    def upload_file(self,
                    filename: Union[str, pathlib.Path],
                    metamapper: Optional[Callable[[Union[str, pathlib.Path]], pathlib.Path]] = None,
                    auto_map_hdf: bool = True,
                    overwrite: bool = False,
                    **metamapper_kwargs):
        """Upload a file to the repository. A metamapper function can be provided optionally. It
        extracts metadata from the target file and also uploads it to the repository. This feature is especially
        useful for large files and especially for HDF5 files. Although the method call is very basic and does not
        further specify the metamapper function behaviour, the intended output (meta) file should be a JSON-LD
        file for the sake of interoperability. Ultimately, the metadata file should be downloaded first by the user
        interested in the repository data, in order to understand the file content. This avoids downloading a very
        large file, which might not be needed.

        Implementation details/requirements for the metamapper function:
        - Takes the filename as first argument. Other kwargs may be provided via metamapper_kwargs
        - Must return the filename of the metadata file

        Parameter
        --------
        filename: Union[str, pathlib.Path]
            The filename of the file to be uploaded.
        metamapper: Optional[None, Callable[[Union[str, pathlib.Path]], pathlib.Path]]
            A function that extracts metadata from the target file and stores it in a file. The filename of the
            metadata file is returned by the function. If None, no metadata is extracted.
        auto_map_hdf: bool=True
            Whether to automatically use the default metamapper function for HDF5 files. If True and the filename
            is scanned for its suffix ('.h5', '.hdf', '.hdf5'), the default metamapper function is used (hdf2jsonld).
        overwrite: bool=False
            If True, the file will be overwritten if it already exists in the repository. If False, an error
            will be raised if the file already exists.
        metamapper_kwargs: dict
            Additional keyword arguments for the metamapper function.

        """
        if not pathlib.Path(filename).exists():
            raise FileNotFoundError(f'The file {filename} does not exist.')

        if metamapper is None and auto_map_hdf and pathlib.Path(filename).suffix in ('.hdf', '.hdf5', '.h5'):
            metamapper = _HDF2JSON

        if metamapper is not None:
            meta_data_file = metamapper(filename, **metamapper_kwargs)
        else:
            meta_data_file = None

        self.__upload_file__(filename=filename, overwrite=overwrite)

        if meta_data_file is not None:
            self.__upload_file__(filename=meta_data_file, overwrite=overwrite)
        self.refresh()

    @deprecated(version='1.4.0rc1',
                msg='This method is deprecated. '
                    'Use `.upload_file(...)` instead and provide the '
                    'metamapper parameter there')
    def upload_hdf_file(self,
                        filename,
                        metamapper: Callable[[Union[str, pathlib.Path]], pathlib.Path],
                        overwrite: bool = False):
        """Upload an HDF5 file. Additionally, a metadata file will be extracted from the
        HDF5 file using the metamapper function and is uploaded as well.
        The metamapper function takes a filename, extracts the metadata and stores it in
        a file. The filename of it is returned by the function. It is automatically uploaded
        with the HDF5 file.

        .. note::

            This method is deprecated. Use `upload_file` instead and provide the metamapper
            function there.


        """
        warnings.warn('This method is deprecated. Use `upload_file` instead and provide the '
                      'metamapper parameter there', DeprecationWarning)
        return self.upload_file(filename, metamapper, overwrite)

    @abc.abstractmethod
    def get_doi(self):
        """Get the DOI of the repository."""

    @abc.abstractmethod
    def get_jsonld(self) -> str:
        """Returns the JSONLD representation of the repository"""
