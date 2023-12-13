import abc
import requests
from typing import Union

from .config import get_api_token
from .metadata import Metadata


class AbstractZenodoRecord(abc.ABC):
    """An abstract Zenodo record."""
    base_url = None

    def __init__(self, metadata: Metadata, deposit_id: Union[int, None] = None):
        self.deposit_id = deposit_id
        self.metadata = metadata
        if self.base_url is None:
            raise ValueError('The base_url must be set.')

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


class ZenodoRecordInterface(AbstractZenodoRecord):

    def __init__(self, metadata: Metadata, deposit_id: Union[int, None] = None):
        self.deposit_id = deposit_id
        self.metadata = metadata
        if self.base_url is None:
            raise ValueError('The base_url must be set.')

    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo."""
        if self.deposit_id is None:
            return False

        base_url = self.base_url + f'/{self.deposit_id}'
        r = requests.get(
            base_url,
            params={'access_token': get_api_token(sandbox=True)}
        )
        if r.status_code == 404:
            return False
        return True

    def create(self):
        """Create (not publish!) a new deposit on Zenodo."""
        data = {'metadata': self.metadata.model_dump()
                }
        r = requests.post(
            self.base_url,
            json=data,
            params={"access_token": get_api_token(sandbox=True)},
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        self.deposit_id = r.json()['id']
        return self.deposit_id

    def delete(self):
        print('getting deposit {self.deposit_id}')
        r = requests.get(
            f'https://sandbox.zenodo.org/api/deposit/depositions/{self.deposit_id}',
            params={'access_token': get_api_token(sandbox=True)}
        )
        r.raise_for_status()
        print('deleting deposit {self.deposit_id}')
        r = requests.delete(
            'https://sandbox.zenodo.org/api/deposit/depositions/{}'.format(r.json()['id']),
            params={'access_token': get_api_token(sandbox=True)}
        )
        r.raise_for_status()

    def update(self):
        pass

    def publish(self):
        """Be careful. The record cannot be deleted afterwards!"""


class ZenodoRecord(ZenodoRecordInterface):
    base_url = 'https://zenodo.org/api/deposit/depositions'


class ZenodoSandboxRecord(ZenodoRecordInterface):
    """A Zenodo record in the sandbox environment."""
    base_url = 'https://sandbox.zenodo.org/api/deposit/depositions'
