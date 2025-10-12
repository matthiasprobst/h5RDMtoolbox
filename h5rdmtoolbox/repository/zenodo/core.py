import abc
import copy
import json
import logging
import pathlib
import time
import warnings
from typing import Union, Dict, Optional

import requests
from packaging.version import Version
from rdflib import Graph

from .metadata import Metadata
from .tokens import get_api_token
from ..interface import RepositoryInterface, RepositoryFile

logger = logging.getLogger('h5rdmtoolbox')

IANA_DICT = {
    '.json': 'application/json',
    '.jsonld': 'application/ld+json',
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.tiff': 'image/tiff',
    '.yaml': 'application/x-yaml',
}


class APIError(Exception):
    """Raised when an API error occurs."""


class AbstractZenodoInterface(RepositoryInterface, abc.ABC):
    """Interface for Zenodo.

    Procedure to update metadata (replace `AbstractZenodoInterface` with `ZenodoSandboxDeposit` or `ZenodoRecord`):
    >>> repo = AbstractZenodoInterface(rec_id=12345)
    >>> metadata = repo.get_metadata()
    >>> metadata['title'] = 'New title' # changing metadata
    >>> repo.unlock()
    >>> repo.set_metadata(metadata)
    >>> repo.publish()

    Procedure to create a new version (replace `AbstractZenodoInterface` with `ZenodoSandboxDeposit` or `ZenodoRecord`):
    >>> repo = AbstractZenodoInterface(rec_id=12345)
    >>> new_repo = repo.new_version(version='1.2.3')
    """

    def __init__(self,
                 source: Union[int, str, None] = None,
                 rec_id=None,
                 env_name_for_token: Optional[str] = None):
        """Initialize the ZenodoInterface.

        Parameters
        ----------
        source : int, str, None
            The rec_id or url of the deposit. If None, a new deposit will be created.
            If a rec_id is passed, the deposit must exist.

        """
        self.env_name_for_token = env_name_for_token
        self._cached_json = {}
        if rec_id is not None:
            warnings.warn("The `rec_id` parameter is deprecated. Please use the source parameter instead.",
                          DeprecationWarning)
            source = rec_id

        if isinstance(source, int):
            rec_id = source
        elif isinstance(source, str):
            """assuming it is a url"""
            if not source.startswith('http'):
                raise ValueError(f"String input should be a valid URL, which {source} seems not to be. If you intend "
                                 "to provide a record id, please provide an integer.")
            if source.startswith(f"{self.base_url}/record"):
                rec_id = int(source.split('/')[-1])
            elif source.startswith('https://doi.org/'):
                r = requests.get(source, allow_redirects=True)
                # the redirected url contains the ID:
                rec_id = int(r.url.split('/')[-1])
        elif source is None:
            # create a new deposit (with new rec_id and without metadata!)
            r = requests.post(
                self.depositions_url,
                json={},
                params={"access_token": self.access_token},
                headers={"Content-Type": "application/json"}
            )
            r.raise_for_status()
            rec_id = r.json()['id']
        self.rec_id = rec_id
        assert self.rec_id is not None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} (id={self.rec_id}, url={self.record_url})"

    # @property
    # def identifier(self) -> Union[str, None]:
    #     identifier = self.get_metadata().get('identifier', None)
    #     if identifier is None:
    #         return self.get_metadata().get('prereserve_doi', {}).get('recid', 'no identifier found')
    #     return identifier

    # @property
    # def title(self):
    #     return self.get_metadata().get('title', 'No title')

    @property
    @abc.abstractmethod
    def base_url(self):
        """Return the base url, e.g. 'https://sandbox.zenodo.org'"""

    @property
    def depositions_url(self):
        return f"{self.base_url}/api/deposit/depositions"

    @property
    def identifier(self):
        return self.get_metadata()['identifier']

    @property
    def title(self):
        return self.get_metadata()['title']

    @property
    def records_url(self):
        return f"{self.base_url}/api/deposit/depositions"

    @property
    def record_url(self):
        """Return the (published) url. Note, that it must not necessarily exist if you
        just created a new record and have not published it yet!"""
        return f"{self.base_url}/records/{self.rec_id}"

    @abc.abstractmethod
    def get_metadata(self) -> Dict:
        """Return metadata"""

    @abc.abstractmethod
    def set_metadata(self, metadata: Union[Dict, Metadata]):
        """Set metadata"""

    def get_doi(self) -> str:
        """Get the DOI of the deposit."""
        doi = self.get_metadata().get('doi', None)
        if doi is None:
            return self.get_metadata()['prereserve_doi']['doi']
        return doi

    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo. Note, that only published records are detected!"""
        return requests.get(self.record_url, params={'access_token': self.access_token}).ok

    def is_published(self) -> bool:
        """Check if the deposit is published."""
        return self._get()['submitted']

    submitted = is_published  # alias

    def json(self, raise_for_status: bool = False):
        """Get the deposit (json) data."""
        if not self._cached_json:
            url = f"{self.depositions_url}/{self.rec_id}"
            access_token = self.access_token
            r = requests.get(url, params={"access_token": access_token})

            if r.status_code == '403':
                logger.critical(
                    f"You don't have the permission to request {url}. You may need to check your access token.")
                r.raise_for_status()

            while r.status_code == 429:
                logger.info(f"Too many requests message: {r.json()}. Sleep for 60 seconds and try again.")
                time.sleep(60)
                r = requests.get(url, params={"access_token": access_token})

            while r.status_code == 500:
                logger.info(f"Internal error: {r.json()}. Sleep for 60 seconds and try again.")
                time.sleep(60)
                r = requests.get(url, params={"access_token": access_token})

            if raise_for_status:
                r.raise_for_status()

            self._cached_json = r.json()
        return self._cached_json

    @property
    def files(self) -> Dict[str, RepositoryFile]:
        is_submitted = self.submitted()

        def _parse_download_url(url, filename):
            if url is None:
                return url
            if is_submitted:
                return f"{self.record_url}/files/{filename}"
            if url.endswith('/content'):
                return url.rsplit('/', 1)[0]
            return url

        def _get_media_type(filename: Optional[str]):
            if filename is None:
                return None
            suffix = pathlib.Path(filename).suffix

            return IANA_DICT.get(suffix, suffix[1:])

        def _parse(data: Dict):
            return dict(download_url=_parse_download_url(data['links']['download'], data['filename']),
                        access_url=f"https://doi.org/{self.get_doi()}",
                        name=data.get('filename', None),
                        media_type=_get_media_type(data.get('filename', None)),
                        identifier=data.get('id', None),
                        identifier_url=data.get('id', None),
                        size=data.get('filesize', None),
                        checksum=data.get('checksum', None),
                        access_token=self.access_token)

        rfiles = [RepositoryFile(**_parse(data)) for data in self._get()['files']]
        return {f.name: f for f in rfiles}

    def download_file(self, filename: str, target_folder: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
        """Download a file based on URL. The url is validated using pydantic

        Parameters
        ----------
        filename : str
            The filename.
        target_folder : Union[str, pathlib.Path], optional
            The target folder, by default None
            If None, the file will be downloaded to the default folder, which is in
            the user data directory of the h5rdmtoolbox package.

        Returns
        -------
        pathlib.Path
            The path to the downloaded file.
        """
        warnings.warn("Please use `.files.get(filename).download()`", DeprecationWarning)
        f = self.files.get(filename)
        return f.download(target_folder=target_folder)

    def delete(self) -> requests.Response:
        """Delete the deposit."""
        r = requests.delete(f"{self.depositions_url}/{self.rec_id}", params={"access_token": self.access_token})
        if r.status_code == 405:
            logger.error(f'Only unpublished records can be deleted. Record "{self.rec_id}" is published.')
        return r

    def new_version(self, new_version_string: str):
        """Sets the record into edit mode while creating a new version. You need to call `.publish()` after
        adding new files, metadata etc.

        Parameters
        ----------
        new_version_string : str
            The new version string. It must be higher than the current version. This
            is checked using the `packaging.version.Version` class.

        Returns
        -------
        ZenodoInterface
            The new ZenodoInterface with the new version.

        Raises
        ------
        ValueError
            If the new version is not higher than the current version.
        APIError
            If the new version cannot be created because permission is missing.
        """
        self.unlock()
        jdata = self.json()

        curr_version = Version(jdata['metadata']['version'])
        new_version = Version(new_version_string)
        if not new_version > curr_version:
            raise ValueError(f'The new version must be higher than the current version {curr_version}.')

        new_vers_url = jdata['links'].get('newversion', None)
        if new_vers_url is None:
            raise APIError("Unable to create a new version. Please check your permission associated with "
                           "the Zenodo API Token.")

        headers = {'Authorization': f'Bearer {self.access_token}'}
        r = requests.post(
            new_vers_url,
            headers=headers
        )

        r.raise_for_status()
        self._cached_json = r.json()
        latest_draft = r.json()['links']['latest_draft']
        _id = latest_draft.split('/')[-1]
        self.rec_id = _id
        current_metadata = self.get_metadata()
        current_metadata['version'] = new_version_string
        self.set_metadata(current_metadata)
        return self

    def publish(self):
        """Be careful. The record cannot be deleted afterward!"""
        url = f"{self.base_url}/api/deposit/depositions/{self.rec_id}/actions/publish"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        r = requests.post(url,
                          # data=json.dumps({'publication_date': '2024-03-03', 'version': '1.2.3'}),
                          headers=headers)
        if "errors" in r.json():
            for err in r.json()["errors"]:
                logger.error(f"Error publishing record: {err}")
        r.raise_for_status()
        self._cached_json = r.json()
        return self
        # self.refresh()

    def discard(self):
        """Discard the latest action, e.g. creating a new version"""
        jdata = self.json()
        r = requests.post(jdata['links']['discard'],
                          params={'access_token': self.access_token})
        r.raise_for_status()

    def unlock(self):
        """unlock the deposit. To lock it call publish()

        Raises
        ------
        APIError
            If the record cannot be unlocked because permission is missing.
        """
        edit_url = self.json()['links'].get('edit', None)
        if edit_url is None:
            raise APIError('Unable to unlock the record. Please check your permission of the Zenodo API Token.')

        r = requests.post(edit_url,
                          params={'access_token': self.access_token})
        if r.status_code == 400:
            print(f'Cannot publish data. This might be because metadata is missing. Check on the website, which '
                  f'fields are required!')
        r.raise_for_status()

    @property
    @abc.abstractmethod
    def access_token(self) -> str:
        """Return the api token for the Zenodo API."""


class ZenodoRecord(RepositoryInterface):
    """Interface to Zenodo records.

    .. note: If you want to use the sandbox (testing) environment,
        please init with sandbox=True.
    """

    def __init__(self,
                 source: Union[int, str, None] = None,
                 sandbox: bool = False,
                 env_name_for_token: Optional[str] = None,
                 **kwargs):
        self.env_name_for_token = env_name_for_token
        rec_id = kwargs.pop('rec_id', None)
        if rec_id is not None:
            warnings.warn("The `rec_id` parameter is deprecated. Please use the source parameter instead.",
                          DeprecationWarning)
            source = rec_id
        self.sandbox = sandbox
        self._cached_json = {}
        if isinstance(source, int):
            rec_id = source
        elif isinstance(source, str):
            """assuming it is a url"""
            if not source.startswith('http'):
                raise ValueError(f"String input should be a valid URL, which {source} seems not to be. If you intend "
                                 "to provide a record id, please provide an integer.")
            if source.startswith(f"{self.base_url}/record"):
                rec_id = int(source.split('/')[-1])
            elif source.startswith('https://doi.org/'):
                r = requests.get(source, allow_redirects=True)
                # the redirected url contains the ID:
                rec_id = int(r.url.split('/')[-1])
        elif source is None:
            # create a new deposit (with new rec_id and without metadata!)
            r = requests.post(
                self.depositions_url,
                json={},
                params={"access_token": self.access_token},
                headers={"Content-Type": "application/json"}
            )
            r.raise_for_status()
            rec_id = r.json()['id']
        self.rec_id = rec_id
        assert self.rec_id is not None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} (id={self.rec_id}, url={self.record_url})"

    @property
    def identifier(self) -> str:
        identifier = self.get_metadata().get('identifier', None)
        if identifier is None:
            return self.get_metadata().get('prereserve_doi', {}).get('recid', 'no identifier found')
        return identifier

    @property
    def title(self):
        return self.get_metadata().get('title', 'No title')

    @property
    def base_url(self) -> str:
        """Returns the base url of the repository"""
        if self.sandbox:
            return 'https://sandbox.zenodo.org'
        return 'https://zenodo.org'

    @property
    def depositions_url(self):
        return f"{self.base_url}/api/deposit/depositions"

    @property
    def records_url(self):
        return f"{self.base_url}/api/deposit/depositions"

    @property
    def record_url(self):
        """Return the (published) url. Note, that it must not necessarily exist if you
        just created a new record and have not published it yet!"""
        return f"{self.base_url}/records/{self.rec_id}"

    @property
    def access_token(self):
        """Get the access token for the Zenodo API. This is needed to upload files."""
        return get_api_token(sandbox=self.sandbox, env_var_name=self.env_name_for_token)

    def _get(self):
        url = f"{self.depositions_url}/{self.rec_id}"
        access_token = self.access_token
        r = requests.get(url, params={"access_token": access_token})
        return r.json()

    def get_metadata(self) -> Dict:
        return self._get()['metadata']

    def set_metadata(self, metadata: Union[Dict, Metadata]):
        """update the metadata of the deposit"""
        if isinstance(metadata, dict):
            metadata = Metadata(**metadata)

        if not isinstance(metadata, Metadata):
            raise TypeError('The metadata must be of type Metadata, not {type(metadata)}')

        url_latest_draft = f"{self.depositions_url}/{self.rec_id}"
        r = requests.put(
            url_latest_draft,
            data=json.dumps(dict(metadata=metadata.model_dump(exclude_none=True))),
            params={"access_token": self.access_token},
            # headers={"Content-Type": "application/json"}
        )
        if r.status_code == 400:
            logger.critical(f"Bad request message: {r.json()}")
        r.raise_for_status()
        self.rec_id = r.json()["id"]

    def get_doi(self) -> str:
        """Get the DOI of the deposit."""
        metadata = self.get_metadata()
        doi = metadata.get('doi', None)
        if doi is None:
            return metadata['prereserve_doi']['doi']
        return doi

    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo. Note, that only published records are detected!"""
        return requests.get(self.record_url, params={'access_token': self.access_token}).ok

    def is_published(self) -> bool:
        """Check if the deposit is published."""
        return self._get()['submitted']

    submitted = is_published  # alias

    # def json(self, raise_for_status: bool = False):
    #     """Get the deposit (json) data."""
    #     if not self._cached_json:
    #         url = f"{self.depositions_url}/{self.rec_id}"
    #         access_token = self.access_token
    #         r = requests.get(url, params={"access_token": access_token})
    #
    #         if r.status_code == 403:
    #             logger.critical(
    #                 f"You don't have the permission to request {url}. You may need to check your access token.")
    #             r.raise_for_status()
    #
    #         while r.status_code == 429:
    #             logger.info(f"Too many requests message: {r.json()}. Sleep for 60 seconds and try again.")
    #             time.sleep(60)
    #             r = requests.get(url, params={"access_token": access_token})
    #
    #         while r.status_code == 500:
    #             logger.info(f"Internal error: {r.json()}. Sleep for 60 seconds and try again.")
    #             time.sleep(60)
    #             r = requests.get(url, params={"access_token": access_token})
    #
    #         if raise_for_status:
    #             r.raise_for_status()
    #
    #         self._cached_json = r.json()
    #     return self._cached_json

    # def refresh(self) -> None:
    #     """Since the json dict is cached, calling this method will refresh the json dict."""
    #     self._cached_json = {}
    #     self.json()

    @property
    def files(self) -> Dict[str, RepositoryFile]:
        # def _parse_download_url(filename):
        #     if filename is None:
        #         return filename
        #     return f"{self.rec_url}/{self.rec_id}/files/{filename}"

        is_submitted = self.submitted()

        def _parse_download_url(url, filename):
            if url is None:
                return url
            if is_submitted:
                return f"{self.record_url}/files/{filename}"
            if url.endswith('/content'):
                return url.rsplit('/', 1)[0]
            return url

        def _get_media_type(filename: Optional[str]):
            if filename is None:
                return None
            suffix = pathlib.Path(filename).suffix

            return IANA_DICT.get(suffix, suffix[1:])

        def _parse(data: Dict):
            return dict(download_url=_parse_download_url(data['links']['download'], data['filename']),
                        access_url=f"https://doi.org/{self.get_doi()}",
                        name=data.get('filename', None),
                        media_type=_get_media_type(data.get('filename', None)),
                        identifier=data.get('id', None),
                        identifier_url=data.get('id', None),
                        size=data.get('filesize', None),
                        checksum=data.get('checksum', None),
                        access_token=self.access_token)

        rfiles = [RepositoryFile(**_parse(data)) for data in self._get()['files']]
        return {f.name: f for f in rfiles}

    def download_file(self, filename: str, target_folder: Optional[Union[str, pathlib.Path]] = None) -> pathlib.Path:
        """Download a file based on URL. The url is validated using pydantic

        Parameters
        ----------
        filename : str
            The filename.
        target_folder : Union[str, pathlib.Path], optional
            The target folder, by default None
            If None, the file will be downloaded to the default folder, which is in
            the user data directory of the h5rdmtoolbox package.

        Returns
        -------
        pathlib.Path
            The path to the downloaded file.
        """
        warnings.warn("Please use `.files.get(filename).download()`", DeprecationWarning)
        return self.files.get(filename).download(target_folder=target_folder)

    def delete(self) -> requests.Response:
        """Delete the deposit."""
        r = requests.delete(f"{self.depositions_url}/{self.rec_id}", params={"access_token": self.access_token})
        if r.status_code == 405:
            logger.error(f'Only unpublished records can be deleted. Record "{self.rec_id}" is published.')
        return r

    def new_version(self, new_version_string: str):
        """Sets the record into edit mode while creating a new version. You need to call `.publish()` after
        adding new files, metadata etc.

        Parameters
        ----------
        new_version_string : str
            The new version string. It must be higher than the current version. This
            is checked using the `packaging.version.Version` class.

        Returns
        -------
        ZenodoInterface
            The new ZenodoInterface with the new version.

        Raises
        ------
        ValueError
            If the new version is not higher than the current version.
        APIError
            If the new version cannot be created because permission is missing.
        """
        self.unlock()
        jdata = self._get()

        curr_version = Version(jdata['metadata']['version'])
        new_version = Version(new_version_string)
        if not new_version > curr_version:
            raise ValueError(f'The new version must be higher than the current version {curr_version}.')

        new_vers_url = self.get_actions_url("newversion")

        r = requests.post(new_vers_url,
                          params={'access_token': self.access_token})

        r.raise_for_status()
        latest_draft = r.json()['links']['latest_draft']
        _id = latest_draft.split('/')[-1]

        new_record = copy.deepcopy(self)
        new_record.rec_id = _id
        current_metadata = new_record.get_metadata()
        current_metadata["version"] = str(new_version)
        new_record.set_metadata(current_metadata)
        return new_record

    def publish(self) -> requests.Response:
        """Be careful. The record cannot be deleted afterward!"""
        url = self.get_actions_url("publish")
        r = requests.post(url,
                          # data=json.dumps({'publication_date': '2024-03-03', 'version': '1.2.3'}),
                          params={'access_token': self.access_token})
        r.raise_for_status()
        self.rec_id = r.json()['id']
        return r

    def get_actions_url(self, action: str) -> str:
        return f"{self.base_url}/api/deposit/depositions/{self.rec_id}/actions/{action}"

    def discard(self):
        """Discard the latest action, e.g. creating a new version"""
        jdata = self._get()
        r = requests.post(jdata['links']['discard'],
                          params={'access_token': self.access_token})
        r.raise_for_status()

    def unlock(self):
        """unlock the deposit. To lock it call publish()

        Raises
        ------
        APIError
            If the record cannot be unlocked because permission is missing.
        """
        edit_url = self._get()['links'].get('edit', None)
        if edit_url is None:
            raise APIError('Unable to unlock the record. Please check your permission of the Zenodo API Token.')

        r = requests.post(edit_url,
                          params={'access_token': self.access_token})
        if r.status_code == 400:
            print(f'Cannot publish data. This might be because metadata is missing. Check on the website, which '
                  f'fields are required!')
        r.raise_for_status()

    def __upload_file__(self, filename, overwrite: bool = False):
        """Uploading file to record"""
        filename = pathlib.Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f'File "{filename}" does not exist.')

        existing_filenames = [file.name for file in self.files.values()]
        file_exists_in_record = filename.name in existing_filenames

        if not overwrite and file_exists_in_record:
            logger.debug(f'Overwriting file "{filename}" in record "{self.rec_id}"')
            warnings.warn(f'Filename "{filename}" already exists in deposit. Skipping..."', UserWarning)
            return

        # file exists in record. get file id
        if file_exists_in_record:
            file_id = self.files.get(filename.name).identifier
            url = f"{self.depositions_url}/{self.rec_id}/files/{file_id}"
            logger.debug(f'requests.delete(url={url}, ...)')
            r = requests.delete(url=url,
                                params={'access_token': self.access_token})
            r.raise_for_status()

        # https://developers.zenodo.org/?python#quickstart-upload
        bucket_url = self._get()["links"]["bucket"]
        logger.debug(f'adding file "{filename}" to record "{self.rec_id}"')
        with open(filename, "rb") as fp:
            r = requests.put(f"{bucket_url}/{filename.name}",
                             data=fp,
                             params={"access_token": self.access_token},
                             )
            if r.status_code == 403:
                logger.critical(
                    f"Access denied message: {r.json()}. This could be because the record is published. "
                    f"You can only modify metadata.")
            r.raise_for_status()

    def export(self, fmt, target_filename: Optional[Union[str, pathlib.Path]] = None):
        """Exports the record (see Export button on record website). Format must be one of the
        possible options, e.g. dcat.ap, json, ..."""
        if target_filename is None:
            from ...utils import generate_temporary_filename
            target_filename = generate_temporary_filename()
        else:
            target_filename = pathlib.Path(target_filename)

        export_url = f"{self._get()['links']['html']}/export/{fmt}"
        r = requests.get(export_url)
        r.raise_for_status()
        with open(target_filename, 'wb') as f:
            f.write(r.content)

        return target_filename

    def get_jsonld(self) -> str:
        """Return the json-ld representation of the record."""
        tmp_dcat_filename = self.export(fmt='dcat-ap')
        g = Graph()
        g.parse(tmp_dcat_filename, format='xml')
        return g.serialize(format='json-ld',
                           indent=4,
                           context={'dcat': 'http://www.w3.org/ns/dcat#',
                                    'foaf': 'http://xmlns.com/foaf/0.1/',
                                    'adms': 'http://www.w3.org/ns/adms#',
                                    'skos': 'http://www.w3.org/2004/02/skos/core#',
                                    'dcterms': 'http://purl.org/dc/terms/',
                                    'org': 'http://www.w3.org/ns/org#',
                                    'xsd': 'http://www.w3.org/2001/XMLSchema#',
                                    'owl': 'http://www.w3.org/2002/07/owl#',
                                    'dctype': 'http://purl.org/dc/dcmitype/'
                                    })
