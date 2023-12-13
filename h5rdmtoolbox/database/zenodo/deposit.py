import abc
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

    def __init__(self, metadata: Metadata, deposit_id: Union[int, None] = None):
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


class ZenodoRecordInterface(AbstractZenodoRecord):

    def __init__(self,
                 metadata: Metadata,
                 deposit_id: Union[int, None] = None,
                 file_or_filenames: Union[List[Union[str, pathlib.Path]], None] = None):
        self.deposit_id = deposit_id
        self.metadata = metadata
        self.filenames = []

        if file_or_filenames is not None:
            if isinstance(file_or_filenames, (str, pathlib.Path)):
                self.add_file(file_or_filenames)
            elif isinstance(file_or_filenames, (tuple, list)):
                self.add_file(*file_or_filenames)
            else:
                raise TypeError(
                    'file_or_filenames must be a string, pathlib.Path, or a list of strings or pathlib.Path. '
                    f'Got {type(file_or_filenames)} instead.')

    def _get(self, raise_for_status: bool = False):
        """Get the deposit from Zenodo."""
        base_url = self.base_url + f'/{self.deposit_id}'
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
        r = requests.post(
            self.base_url,
            json=data,
            params={"access_token": self.api_token},
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        self.deposit_id = r.json()['id']
        self._push_files()
        return self.deposit_id

    def _push_files(self):
        """Push the files to the deposit."""

        bucket_url = self._get().json()["links"]["bucket"]
        for filename in self.filenames:
            logger.debug(f'adding file "{filename}" to deposit "{self.deposit_id}"')
            with open(filename, "rb") as fp:
                r = requests.put(
                    "%s/%s" % (bucket_url, filename.name),
                    data=fp,
                    params={"access_token": self.api_token},
                )
                r.raise_for_status()

    def delete(self):
        """Delete the deposit on Zenodo."""
        logger.debug(f'getting deposit "{self.deposit_id}"')
        r = requests.get(
            f'https://sandbox.zenodo.org/api/deposit/depositions/{self.deposit_id}',
            params={'access_token': self.api_token}
        )
        r.raise_for_status()
        logger.debug('deleting deposit {self.deposit_id}')
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
            raise FileNotFoundError(f'{filename} does not exist.')
        self.filenames.append(filename)


class ZenodoRecord(ZenodoRecordInterface):
    base_url = 'https://zenodo.org/api/deposit/depositions'

    @property
    def api_token(self):
        return self.api_token(sandbox=False)


class ZenodoSandboxRecord(ZenodoRecordInterface):
    """A Zenodo record in the sandbox environment."""
    base_url = 'https://sandbox.zenodo.org/api/deposit/depositions'

    @property
    def api_token(self):
        return get_api_token(sandbox=True)
