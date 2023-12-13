import abc
import appdirs
import pathlib
import requests
from typing import List, Union

from h5rdmtoolbox.utils import create_tbx_logger
from .config import get_api_token
from .metadata import Metadata

logger = create_tbx_logger('zenodo')


class AbstractZenodoRecord(abc.ABC):
    """An abstract Zenodo record."""
    base_url = None

    def __init__(self,
                 deposit_id: Union[int, None] = None,
                 metadata: Metadata = None):
        if self.base_url is None:
            raise ValueError('The base_url must be set.')
        self.deposit_id = deposit_id
        self.metadata = metadata
        if self.base_url is None:
            raise ValueError('The base_url must be set.')

    @property
    @abc.abstractmethod
    def api_token(self) -> str:
        """The API token for the Zenodo account."""

    @abc.abstractmethod
    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo."""

    @abc.abstractmethod
    def create(self):
        """Create (not publish!) a new deposit on Zenodo."""

    @abc.abstractmethod
    def delete(self):
        """Delete the deposit on Zenodo."""

    @abc.abstractmethod
    def update(self):
        """Update the deposit."""

    @abc.abstractmethod
    def publish(self):
        """Be careful. The record cannot be deleted afterwards!"""

    @abc.abstractmethod
    def add_file(self, filename):
        """Add a file to the deposit."""

    @abc.abstractmethod
    def download_files(self):
        """Download all (!) files from Zenodo."""

    @abc.abstractmethod
    def download_file(self, name):
        """Download a specific file from Zenodo."""

    @abc.abstractmethod
    def get_filenames(self):
        """Get a list of all filenames."""


class ZenodoRecordInterface(AbstractZenodoRecord):
    """A Zenodo record interface."""

    def __init__(self,
                 deposit_id: Union[int, None] = None,
                 metadata: Metadata = None):
        self.deposit_id = deposit_id
        self._metadata = metadata

    @property
    def metadata(self):
        if self._metadata is None:
            raise ValueError('The metadata must be set.')
        return self._metadata

    @metadata.setter
    def metadata(self, value: Metadata):
        if not isinstance(value, Metadata):
            raise TypeError('The metadata must be a Metadata object.')
        self._metadata = value

    def _get(self, raise_for_status: bool = False):
        """Get the deposit from Zenodo."""
        if self.deposit_id is None:
            raise ValueError('The deposit_id must be set.')
        base_url = self.base_url + f'/{self.deposit_id}'
        if not self.api_token:
            r = requests.get(
                base_url,
            )
        else:
            r = requests.get(
                base_url,
                params={'access_token': self.api_token}
            )
        if raise_for_status:
            r.raise_for_status()
        return r

    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo."""
        if self.deposit_id is None:
            return False
        r = self._get(raise_for_status=False)
        if r.status_code == 404:
            return False
        return True

    def create(self):
        """Create (not publish!) a new deposit on Zenodo."""
        data = {
            'metadata': self.metadata.model_dump()
        }
        if self.deposit_id is not None:
            url = self.base_url + f'/{self.deposit_id}/actions/edit'
        else:
            url = self.base_url
        r = requests.post(
            url,
            json=data,
            params={"access_token": self.api_token},
            headers={"Content-Type": "application/json"}
        )
        logger.debug(f'creating deposit on Zenodo: request response: {r.json()}')
        r.raise_for_status()
        if self.deposit_id is None:
            self.deposit_id = r.json()['id']
        else:
            assert self.deposit_id == r.json()['id']
        return self.deposit_id

    def delete(self):
        """Delete the deposit on Zenodo."""
        logger.debug(f'getting deposit "{self.deposit_id}"')
        if not self.api_token:
            r = requests.get(
                f'https://sandbox.zenodo.org/api/deposit/depositions/{self.deposit_id}',
            )
        else:
            r = requests.get(
                f'https://sandbox.zenodo.org/api/deposit/depositions/{self.deposit_id}',
                params={'access_token': self.api_token}
            )
        r.raise_for_status()
        logger.debug('deleting deposit {self.deposit_id}')
        if not self.api_token:
            r = requests.delete(
                'https://sandbox.zenodo.org/api/deposit/depositions/{}'.format(r.json()['id']),
            )
        else:
            r = requests.delete(
                'https://sandbox.zenodo.org/api/deposit/depositions/{}'.format(r.json()['id']),
                params={'access_token': self.api_token}
            )
        r.raise_for_status()

    def update(self):
        pass

    def publish(self):
        """Be careful. The record cannot be deleted afterwards!"""

    def add_file(self, filename):
        """Add a file to the deposit."""
        filename = pathlib.Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f'File "{filename}" does not exist.')
        bucket_url = self._get().json()["links"]["bucket"]
        logger.debug(f'adding file "{filename}" to deposit "{self.deposit_id}"')
        with open(filename, "rb") as fp:
            r = requests.put(
                "%s/%s" % (bucket_url, filename.name),
                data=fp,
                params={"access_token": self.api_token},
            )
            r.raise_for_status()

    def get_filenames(self):
        """Get a list of all filenames."""
        r = self._get()
        return [f['filename'] for f in r.json()['files']]

    def download_files(self, target_folder: Union[str, pathlib.Path] = None):
        """Download all (!) files from Zenodo."""
        r = self._get()
        download_files = []
        for f in r.json()['files']:
            if target_folder is None:
                target_folder = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo_downloads' / str(
                    self.deposit_id)
                target_folder.mkdir(exist_ok=True, parents=True)
            else:
                target_folder = pathlib.Path(target_folder)
            fname = f["filename"]
            target_filename = target_folder / fname
            if not self.api_token:
                bucket_dict = requests.get(f['links']['self']).json()
            else:
                bucket_dict = requests.get(f['links']['self'],
                                           params={'access_token': self.api_token}).json()
            logger.debug(f'downloading file "{fname}" to "{target_filename}"')
            download_files.append(target_filename)
            with open(target_filename, 'wb') as file:
                file.write(requests.get(bucket_dict['links']['self']).content)
        return download_files

    def download_file(self, name, target_folder: Union[str, pathlib.Path] = None):
        """Download a single file from Zenodo."""
        if target_folder is None:
            target_folder = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo_downloads' / str(
                self.deposit_id)
            target_folder.mkdir(exist_ok=True, parents=True)
        else:
            target_folder = pathlib.Path(target_folder)
        r = self._get()
        for f in r.json()['files']:
            if f['filename'] == name:
                fname = f["filename"]
                target_filename = target_folder / fname
                if not self.api_token:
                    bucket_dict = requests.get(f['links']['self']).json()
                else:
                    bucket_dict = requests.get(f['links']['self'],
                                               params={'access_token': self.api_token}).json()
                logger.debug(f'downloading file "{fname}" to "{target_filename}"')
                with open(target_filename, 'wb') as file:
                    file.write(requests.get(bucket_dict['links']['self']).content)
                return target_filename


class ZenodoRecord(ZenodoRecordInterface):
    """A Zenodo record in the production environment."""
    base_url = 'https://zenodo.org/api/deposit/depositions'

    @property
    def api_token(self) -> str:
        """Get the API token for the production environment."""
        return get_api_token(sandbox=False)


class ZenodoSandboxRecord(ZenodoRecordInterface):
    """A Zenodo record in the sandbox environment."""
    base_url = 'https://sandbox.zenodo.org/api/deposit/depositions'

    @property
    def api_token(self):
        return get_api_token(sandbox=True)
