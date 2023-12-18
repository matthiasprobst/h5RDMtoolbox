import abc
import appdirs
import pathlib
import requests
import time
import warnings
from typing import Union, List, Callable

from h5rdmtoolbox.utils import create_tbx_logger
from .metadata import Metadata
from .tokens import get_api_token
from ..interface import RepositoryInterface

logger = create_tbx_logger('zenodo')

__all__ = ['Metadata']


class ZenodoInterface(RepositoryInterface, abc.ABC):
    """Interface for Zenodo.
    """

    def __init__(self,
                 rec_id: Union[int, None]):
        """Initialize the ZenodoInterface.

        Parameters
        ----------
        rec_id : int or None
            The rec_id of the deposit. If None, a new deposit will be created.
            If a rec_id is passed, the deposit must exist.

        """
        if self.base_url is None:
            raise ValueError('The base_url must be set.')
        if rec_id is None:
            # create a new deposit (with new rec_id and without metadata!)
            r = requests.post(
                self.base_url,
                json={},
                params={"access_token": self.access_token},
                headers={"Content-Type": "application/json"}
            )
            r.raise_for_status()
            rec_id = r.json()['id']

        self.rec_id = rec_id
        if not self.exists():
            raise ValueError(f'The deposit with rec_id {rec_id} does not exist. '
                             f'To create a new one, please pass rec_id=None.')

        assert self.rec_id is not None

    @property
    def metadata(self):
        return self.get().json()['metadata']

    @abc.abstractmethod
    def delete(self):
        """Delete the deposit on Zenodo."""

    @abc.abstractmethod
    def get(self, raise_for_status: bool):
        """Get the deposit (json) data."""

    def get_doi(self) -> str:
        """Get the DOI of the deposit."""
        doi = self.get().json()['metadata'].get('doi', None)
        if doi is None:
            return self.get().json()['metadata']['prereserve_doi']['doi']
        return doi

    def exists(self) -> bool:
        """Check if the deposit exists on Zenodo."""
        if self.rec_id is None:
            return False
        r = self.get(raise_for_status=False)
        if r.status_code == 404:
            return False
        return True


class ZenodoDepositInterface(ZenodoInterface):
    """A Zenodo deposit interface. API TOKEN needed"""
    base_url = None

    @property
    def metadata(self):
        return self.get().json()['metadata']

    @metadata.setter
    def metadata(self, metadata: Metadata):
        """update the metadata of the deposit"""
        if not isinstance(metadata, Metadata):
            raise TypeError('The metadata must be of type Metadata, not {type(metadata)}')
        r = requests.put(
            "%s/%s" % (self.base_url, self.rec_id),
            json={'metadata': metadata.model_dump()},
            params={"access_token": self.access_token},
            headers={"Content-Type": "application/json"}
        )
        if r.status_code == 400:
            logger.critical(f"Bad request message: {r.json()}")
        r.raise_for_status()

    def unlock(self):
        """unlock the deposit. To lock it call publish()"""
        requests.post("%s/%s/actions/edit" % (self.base_url, self.rec_id),
                      params={'access_token': self.access_token})

    def publish(self) -> requests.Response:
        """Be careful. The record cannot be deleted afterwards!"""
        return requests.post(f'{self.base_url}/{self.rec_id}/actions/publish',
                             params={'access_token': self.access_token})

    @property
    @abc.abstractmethod
    def access_token(self) -> str:
        """The API token for the Zenodo account."""

    def get(self, raise_for_status: bool = False):
        """Get the deposit (json) data."""

        def _fetch():
            return requests.get(
                "%s/%s" % (self.base_url, self.rec_id),
                params={"access_token": self.access_token},
            )

        r = _fetch()
        while r.status_code == 429:
            logger.info(f"Too many requests message: {r.json()}. Sleep for 60 seconds and try again.")
            time.sleep(60)
            r = _fetch()

        while r.status_code == 500:
            logger.info(f"Internal error: {r.json()}. Sleep for 60 seconds and try again.")
            time.sleep(60)
            r = _fetch()

        if raise_for_status:
            r.raise_for_status()
        return r

    def get_filenames(self) -> List[str]:
        """Get a list of all filenames."""
        return [f['filename'] for f in self.get().json()['files']]

    def upload_file(self, filename, overwrite: bool = False):
        """Add a file to the deposit."""
        filename = pathlib.Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f'File "{filename}" does not exist.')

        if not overwrite:
            # we need to check if the file already exists
            existing_filenames = self.get_filenames()
            if filename.name in existing_filenames:
                logger.debug(f'Overwriting file "{filename}" in deposit "{self.rec_id}"')
                warnings.warn(f'Filename "{filename}" already exists in deposit. Skipping..."', UserWarning)
                return

        bucket_url = self.get().json()["links"]["bucket"]
        logger.debug(f'adding file "{filename}" to deposit "{self.rec_id}"')
        with open(filename, "rb") as fp:
            r = requests.put(
                "%s/%s" % (bucket_url, filename.name),
                data=fp,
                params={"access_token": self.access_token},
            )
            if r.status_code == 403:
                logger.critical(f"Access denied message: {r.json()}. This could be because the record is published. "
                                f"You can only modify metadata.")
            r.raise_for_status()

    def download_files(self,
                       target_folder: Union[str, pathlib.Path] = None,
                       suffix: Union[str, List[str], None] = None) -> List[pathlib.Path]:
        """Download all (!) files from Zenodo. You may specify one or multiple suffixes to only download certain files.

        Parameters
        ----------
        target_folder : str or pathlib.Path, optional
            The target folder, by default None
        suffix: Union[str, List[str], None], optional=None
            Specify a suffix to only download certain files

        Returns
        -------
        List[pathlib.Path]
            A list of all downloaded files.
        """
        if suffix is None:
            return [self.download_file(filename) for filename in self.get_filenames()]
        if isinstance(suffix, str):
            suffix = [suffix]
        return [self.download_file(filename) for filename in self.get_filenames() if filename.endswith(tuple(suffix))]

    def download_file(self,
                      filename: str,
                      target_folder: Union[str, pathlib.Path] = None):
        """Download a single file from Zenodo.

        Parameters
        ----------
        filename : str
            The filename to download
        target_folder : Union[str, pathlib.Path], optional
            The target folder, by default None
            If None, the file will be downloaded to the default folder, which is in
            the user data directory of the h5rdmtoolbox package.
        """
        if target_folder is None:
            target_folder = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo_downloads' / str(
                self.rec_id)
            target_folder.mkdir(exist_ok=True, parents=True)
        else:
            target_folder = pathlib.Path(target_folder)
        r = self.get()
        for f in r.json()['files']:
            if f['filename'] == filename:
                fname = f["filename"]
                target_filename = target_folder / fname
                bucket_dict = requests.get(f['links']['self'],
                                           params={'access_token': self.access_token}).json()
                logger.debug(f'downloading file "{fname}" to "{target_filename}"')
                with open(target_filename, 'wb') as file:
                    file.write(requests.get(bucket_dict['links']['download'],
                                            params={'access_token': self.access_token}).content)
                return target_filename
        raise KeyError(f'File "{filename}" not found in deposit "{self.rec_id}"')

    def delete(self):
        """Delete the deposit."""
        r = requests.delete(
            "%s/%s" % (self.base_url, self.rec_id),
            params={"access_token": self.access_token},
        )
        r.raise_for_status()


class ZenodoSandboxDeposit(ZenodoDepositInterface):
    base_url = 'https://sandbox.zenodo.org/api/deposit/depositions'

    @property
    def access_token(self):
        return get_api_token(sandbox=True)


class ZenodoRecord(ZenodoInterface):
    base_url = 'https://zenodo.org/api/records'

    def upload_file(self, filename, overwrite: bool = False):
        raise RuntimeError(f'The {self.__class__.__name__} does not support file uploads.')

    def upload_hdf_file(self, filename, metamapper: Callable, overwrite: bool = False):
        raise RuntimeError(f'The {self.__class__.__name__} does not support file uploads.')

    def delete(self):
        raise RuntimeError(f'The {self.__class__.__name__} cannot be deleted.')

    def get(self, raise_for_status: bool = False):
        """Get the deposit (json) data."""
        r = requests.get(
            "%s/%s" % (self.base_url, self.rec_id),
        )
        if raise_for_status:
            r.raise_for_status()
        return r

    def download_file(self, filename, target_folder: Union[str, pathlib.Path] = None):
        """Download a single file from Zenodo."""
        if target_folder is None:
            target_folder = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo_downloads' / str(
                self.rec_id)
            target_folder.mkdir(exist_ok=True, parents=True)
        else:
            target_folder = pathlib.Path(target_folder)
        r = self.get()
        for f in r.json()['files']:
            if f['key'] == filename:
                fname = f["key"]
                target_filename = target_folder / fname
                logger.debug(f'downloading file "{fname}" to "{target_filename}"')
                with open(target_filename, 'wb') as file:
                    file.write(requests.get(f['links']['self']).content)
                return target_filename

    def download_files(self, target_folder: Union[str, pathlib.Path] = None) -> List[pathlib.Path]:
        """Download all (!) files from Zenodo.

        Parameters
        ----------
        target_folder : str or pathlib.Path, optional
            The target folder, by default None

        Returns
        -------
        List[pathlib.Path]
            A list of all downloaded files.
        """
        r = self.get()
        downloaded_files = []
        for f in r.json()['files']:
            if target_folder is None:
                target_folder = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo_downloads' / str(
                    self.rec_id)
                target_folder.mkdir(exist_ok=True, parents=True)
            else:
                target_folder = pathlib.Path(target_folder)
            fname = f["key"]
            target_filename = target_folder / fname
            # bucket_dict = requests.get(f['links']['self']).json()
            logger.debug(f'downloading file "{fname}" to "{target_filename}"')
            downloaded_files.append(target_filename)
            with open(target_filename, 'wb') as file:
                file.write(requests.get(f['links']['self']).content)
        return downloaded_files

    def get_filenames(self) -> List[str]:
        """Get a list of all filenames."""
        return [f['key'] for f in self.get().json()['files']]
