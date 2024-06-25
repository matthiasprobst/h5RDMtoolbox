import abc
import appdirs
import logging
import pathlib
import requests
import warnings
from typing import Callable, Union, Optional, List, Dict

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

    from ..wrapper.jsonld import hdf2jsonld

    return hdf2jsonld(filename=filename, skipND=1)


class RepositoryFile(abc.ABC):

    def __init__(self, identifier,
                 identifier_url,
                 download_url,
                 access_url,
                 checksum,
                 filename,
                 size,
                 media_type,
                 access_token=None,
                 **kwargs):
        self.download_url = download_url
        self.access_url = access_url
        self.checksum = checksum
        self.filename = filename
        self.media_type = media_type
        self.size = size
        self.identifier = identifier
        self.identifier_url = identifier_url
        self.access_token = access_token
        self.additional_data = kwargs

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

    def download(self, target_folder: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
        """Download the file to target_folder. If None, local user dir is used.
        Returns the file location"""
        url = self.download_url
        if target_folder is None:
            target_folder = pathlib.Path(
                appdirs.user_data_dir('h5rdmtoolbox')
            ) / 'zenodo_downloads' / str(self.identifier)
            target_folder.mkdir(exist_ok=True, parents=True)
        else:
            logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
            target_folder = pathlib.Path(target_folder)

        filename = str(url).rsplit('/', 1)[-1]
        target_filename = target_folder / filename
        r = requests.get(url, params={'access_token': self.access_token})
        r.raise_for_status()
        with open(target_filename, 'wb') as file:
            # file.write(r.content)
            for chunk in r.iter_content(chunk_size=10 * 1024):
                file.write(chunk)

        # if r.ok:
        #     # r.json()['links']['content']
        #     _content_response = requests.get(r.json()['links']['content'],
        #                                      params={'access_token': self.access_token})
        #     if _content_response.ok:
        #         with open(target_filename, 'wb') as file:
        #             file.write(_content_response.content)
        #     else:
        #         raise requests.HTTPError(f'Could not download file "{filename}" from Zenodo ({url}. '
        #                                  f'Status code: {_content_response.status_code}')
        # else:
        #     raise requests.HTTPError(f'Could not download file "{filename}" from Zenodo ({url}. '
        #                              f'Status code: {r.status_code}')
        return target_filename


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
    def set_metadata(self, metadata):
        """Set the metadata of the repository."""

    @abc.abstractmethod
    def download_file(self, filename):
        """Download a specific file from the repository."""

    @abc.abstractmethod
    def download_files(self):
        """Download all files from the repository."""

    def get_filenames(self) -> List[str]:
        """Get a list of all filenames."""
        return [file.filename for file in self.files]

    @property
    @abc.abstractmethod
    def files(self) -> List[RepositoryFile]:
        """List of all files in the repository."""

    @abc.abstractmethod
    def _upload_file(self, filename: Union[str, pathlib.Path], overwrite: bool = False):
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

        if metamapper is None and auto_map_hdf and filename.suffix in ('.hdf', '.hdf5', '.h5'):
            metamapper = _HDF2JSON

        if metamapper is not None:
            meta_data_file = metamapper(filename, **metamapper_kwargs)
        else:
            meta_data_file = None

        self._upload_file(filename=filename, overwrite=overwrite)

        if meta_data_file is not None:
            self._upload_file(filename=meta_data_file, overwrite=overwrite)

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
