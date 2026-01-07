import os
import pathlib
from abc import abstractmethod, ABC
from contextlib import contextmanager
from typing import Union, Optional
from urllib.parse import urlparse

import h5py
from ontolutils.ex import dcat

from ..abstracts import DataStore
from ...wrapper.core import File


def _get_filename(downloadURL):
    if str(downloadURL).endswith("/content"):
        filename = str(downloadURL).rsplit("/", 2)[-2]
    else:
        filename = os.path.basename(urlparse(str(downloadURL)).path)
    if filename == '':
        filename = str(downloadURL).rsplit("#", 1)[-1]
    return filename


class HDF5Store(DataStore, ABC):
    """HDF5 data store that downloads and provides access to HDF5 files."""

    __expected_file_types__ = {".h5", ".hdf5", ".hdf"}

    def __init__(self, data_directory: Union[str, pathlib.Path] = None):
        """Initialize HDF5 store.

        Parameters
        ----------
        data_directory : Union[str, pathlib.Path]
            Directory to store downloaded HDF5 files
        """
        if data_directory is None:
            data_directory = pathlib.Path.cwd() / "hdf"
        self.data_directory = pathlib.Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self._file_registry = {}

    def __repr__(self):
        """String representation of the Store."""
        return f"{self.__class__.__name__}(data_directory={self.data_directory})"

    def _upload_file(
            self,
            distribution: dcat.Distribution = None,
            validate: bool = True,
            skip_unsupported: bool = False,
    ):
        """Register an HDF5 file in the store (without downloading)."""
        media_type = distribution.mediaType
        if media_type is not None and media_type.lower() not in {"application/x-hdf5", "application/hdf5",
                                                                 "https://www.iana.org/assignments/media-types/application/x-hdf5",
                                                                 "https://www.iana.org/assignments/media-types/application/hdf5"}:
            raise ValueError(f"Unsupported media type: {media_type}")
        downloadURL = distribution.download_URL
        if downloadURL is None:
            raise ValueError("Distribution must have a downloadURL to register.")
        if downloadURL in self._file_registry:
            return  # already registered
        local_filename = _get_filename(downloadURL=downloadURL)
        entry = {
            "id": str(distribution.id),
            "download_url": str(distribution.download_URL),
            "title": distribution.title,
            "filename": local_filename,
        }
        # save the entry under both the download URL and the distribution ID
        self._file_registry[downloadURL] = entry
        self._file_registry[str(distribution.id)] = entry

    @abstractmethod
    def _get_or_download_file(self, identifier: str) -> pathlib.Path:
        """Download HDF5 file if not already present."""

    @contextmanager
    def open_hdf5_object(self, identifier: str, hdf_name: Optional[str] = None):
        """Open HDF5 file and return object.

        Parameters
        ----------
        identifier : str
            File identifier (URL or path)
        hdf_name : Optional[str]
            Name/path within HDF5 file. If None, returns the root group.

        Returns
        -------
        h5py.Dataset or h5py.Group
            HDF5 object
        """
        local_path = self._get_or_download_file(identifier)

        with h5py.File(local_path, "r") as f:
            if hdf_name is None:
                return f["/"]
            else:
                return f[hdf_name] if hdf_name in f else None

    # def register_file_from_metadata(self, download_url: str, identifier: str):
    #     """Register file from metadata query results."""
    #     self._downloaded_files[identifier] = {
    #         "local_path": None,
    #         "download_url": download_url,
    #         "downloaded": False,
    #     }


class HDF5FileStore(HDF5Store):
    """HDF5 file store that downloads and provides access to HDF5 files. Files are stored locally."""

    def _get_or_download_file(self, download_url: str) -> pathlib.Path:
        """Download HDF5 file if not already present."""
        file_info = self._file_registry.get(download_url)
        if not file_info:
            raise FileNotFoundError(f"File {download_url} not registered in store")

        filename = file_info["filename"]
        local_filename = self.data_directory / filename
        if local_filename.exists():
            return local_filename

        # download to target directory
        dist = dcat.Distribution(
            download_URL=file_info["download_url"]
        )
        return dist.download(
            dest_filename=local_filename,
        )

    def __len__(self):
        """Number of registered files in the store."""
        # Each file is registered under both its download URL and its ID,
        # so we count only unique entries by dividing by 2
        return len(self._file_registry) // 2

    @contextmanager
    def open_hdf5_object(
            self,
            download_url: str,
            object_name: str = None):
        """Open HDF5 file and return object using context manager."""
        local_path = self._get_or_download_file(download_url)
        with File(local_path, "r") as f:
            if object_name is None:
                yield f["/"]
            else:
                yield f[object_name] if object_name in f else None
