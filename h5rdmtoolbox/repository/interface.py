import abc
import logging
import pathlib
from typing import Callable, Union, Optional, Dict

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
                 checksum_algorithm,
                 name,
                 size,
                 media_type,
                 access_token=None,
                 **kwargs):
        self.download_url = download_url
        self.access_url = access_url
        self.checksum = checksum
        self.checksum_algorithm = checksum_algorithm
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
                    filename=self.name,
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

    def download(self,
                 target_folder: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
        """Download the file to target_folder. If None, local user dir is used.
        Returns the file location"""
        from .utils import download_file
        return download_file(
            file_url=self.download_url,
            target_folder=target_folder,
            access_token=self.access_token,
            checksum=self.checksum,
            checksum_algorithm=self.checksum_algorithm,
        )


class RepositoryInterface(abc.ABC):
    """Abstract base class for repository interfaces."""

    @property
    @abc.abstractmethod
    def identifier(self) -> str:
        """Return the identifier of the Repository."""

    @abc.abstractmethod
    def download_file(self, name):
        ...

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

    @property
    @abc.abstractmethod
    def files(self) -> Dict[str, RepositoryFile]:
        """List of all files in the repository."""

    @abc.abstractmethod
    def __upload_file__(self, filename: Union[str, pathlib.Path]):
        """Upload a file to the repository. This is a regular file uploader, hence the
        file can be of any type. This is a private method, which needs to be implemented
        by every repository interface. Will be called by `upload_file`"""

    def upload_file(self,
                    filename: Union[str, pathlib.Path],
                    metamapper: Optional[Callable[[Union[str, pathlib.Path]], pathlib.Path]] = None,
                    auto_map_hdf: bool = True,
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

        self.__upload_file__(filename=filename)

        if meta_data_file is not None:
            self.__upload_file__(filename=meta_data_file)

    @abc.abstractmethod
    def get_doi(self):
        """Get the DOI of the repository."""

    @abc.abstractmethod
    def get_jsonld(self) -> str:
        """Returns the JSONLD representation of the repository"""
