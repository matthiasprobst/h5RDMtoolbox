"""Download utilities for h5rdmtoolbox."""

import atexit
import datetime
import json
import pathlib
import time
import uuid
import warnings
from typing import Dict, Optional, Union, List

import requests
from pydantic import HttpUrl, validate_call
from rdflib.plugins.shared.jsonld.context import Context

from .. import user
from .._version import __version__
from .file_io import (
    _request_with_backoff,
    _download_file,
    get_checksum,
    generate_temporary_filename,
)

logger = __import__("h5rdmtoolbox", fromlist=["logger"]).logger
USER_AGENT_HEADER = {
    "User-Agent": f"h5rdmtoolbox/{__version__} (https://github.com/matthiasprobst/h5rdmtoolbox)",
}


def download_context(
    url_source: Union[HttpUrl, List[HttpUrl]], force_download: bool = False
) -> Context:
    """Download a context file from one URL or list of URLs.
    Will check if a context file is already downloaded and use that one.

    Parameters
    ----------
    url_source : HttpUrl or List[HttpUrl]
        URL or list of URLs to download from.
    force_download : bool, optional
        Force download even if file exists, by default False.

    Returns
    -------
    Context
        RDFLib Context object.

    Examples
    --------
    >>> from h5rdmtoolbox.utils import download_context
    >>> context = download_context('https://raw.githubusercontent.com/codemeta/codemeta/2.0/codemeta.jsonld')
    """
    if not isinstance(url_source, list):
        url_source = [url_source]

    filenames = []
    for url in url_source:
        _url = str(url)
        _fname = _url.rsplit("/", 1)[-1]
        context_file = user.UserDir["cache"] / _fname
        if not context_file.exists() or force_download:
            logger.debug(f"Downloading context file from {_url} to {context_file}")
            try:
                with open(context_file, "wb") as f:
                    r = _request_with_backoff("GET", _url)
                    f.write(r.content)
            except requests.RequestException:
                raise RuntimeError(f"Failed to download context file from {_url}")
        filenames.append(str(context_file))
    return Context(filenames)


def download_file(
    url,
    known_hash=None,
    target_folder: Optional[pathlib.Path] = None,
    checksum: Optional[str] = None,
    params: Optional[Dict] = None,
):
    """Downloads the file or returns the already downloaded file.

    Parameters
    ----------
    url : str
        URL to download from.
    known_hash : str, optional
        Expected SHA256 hash of the file.
    target_folder : pathlib.Path, optional
        Target folder to save the file.
    checksum : str, optional
        Checksum of the file.
    params : dict, optional
        Query parameters for the request.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.
    """
    dfm = DownloadFileManager()
    return dfm.download(
        url,
        target_folder=target_folder,
        known_hash=known_hash,
        checksum=checksum,
        params=params,
    )


class DownloadFileManager:
    """Manager for downloading files. By registering checksums and filenames, the manager can be used to
    download files from a remote location. The manager will check if the file is already downloaded and if the
    checksum matches. If the file is not downloaded, it will be downloaded and the checksum will be checked.

    This class is a singleton, hence only one instance can be created."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DownloadFileManager, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self):
        from ..user import CACHE_DIR, USER_DATA_DIR

        self.file_directory = CACHE_DIR
        self.file_directory.mkdir(parents=True, exist_ok=True)
        self.registry: Dict[str, Dict[str, str]] = self.load_registry()
        atexit.register(self.save_registry)

    def __len__(self):
        return len(self.registry)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.file_directory})"

    @property
    def registry_filename(self) -> pathlib.Path:
        return USER_DATA_DIR / "download_registry.json"

    def add(
        self,
        *,
        url: str,
        filepath: pathlib.Path,
        filename: str,
        checksum: Optional[str] = None,
    ):
        """Add to registry. Computes the checksum if not provided.

        Parameters
        ----------
        url : str
            URL the file was downloaded from.
        filepath : pathlib.Path
            Path to the file.
        filename : str
            Original filename.
        checksum : str, optional
            SHA256 checksum of the file.
        """
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} does not exist!")
        if checksum is None:
            checksum = get_checksum(filepath)
            logger.debug(f"Checksum for {filepath} computed: {checksum}")
        self.registry[checksum] = {
            "url": str(url),
            "filepath": str(filepath.resolve()),
            "filename": filename,
        }
        self.save_registry()

    def get(self, checksum: str, filename: str) -> Optional[pathlib.Path]:
        """Returns the file path from the registry based on checksum and filename.

        Parameters
        ----------
        checksum : str
            SHA256 checksum.
        filename : str
            Filename to look up.

        Returns
        -------
        pathlib.Path or None
            Path to the file if found, None otherwise.
        """
        entry = self.registry.get(checksum)
        if entry and entry.get("filename") == filename:
            path = pathlib.Path(entry["filepath"])
            if path.exists():
                return path
        return None

    def remove(self, checksum: str, filename: str):
        """Removes a file from the registry based on checksum and filename.

        Parameters
        ----------
        checksum : str
            SHA256 checksum.
        filename : str
            Filename to remove.
        """
        entry = self.registry.get(checksum)
        if entry and entry.get("filename") == filename:
            self.registry.pop(checksum)
            self.save_registry()
            logger.info(f"File removed: {filename} with checksum: {checksum}")
        else:
            logger.warning(f"No entry found for: {filename} with checksum: {checksum}")

    def remove_corrupted_file(self, filename: pathlib.Path):
        """Removes a corrupted file from the registry.

        Parameters
        ----------
        filename : pathlib.Path
            Path to the corrupted file.
        """
        logger.info(f"Removing corrupted file from registry: {filename}")
        remove_keys = []
        for k, v in self.registry.items():
            if pathlib.Path(self.registry[k].get("filepath", None)) == pathlib.Path(
                filename
            ):
                remove_keys.append(k)
        for k in remove_keys:
            self.registry.pop(k)

    def save_registry(self):
        """Save the registry to disk."""
        max_tries = 10
        n_tries = 0
        self.registry_filename.parent.mkdir(parents=True, exist_ok=True)
        while n_tries < max_tries:
            try:
                with open(self.registry_filename, "w") as f:
                    json.dump(self.registry, f, indent=2)
                return
            except PermissionError:
                logger.debug(f"Could not save registry. Trying again in 0.1s")
                n_tries += 1
                time.sleep(0.1)
        logger.debug(
            f"Could not save registry after {max_tries} tries. File seems to be locked."
        )

    def load_registry(self) -> Dict[str, str]:
        """Load the registry from disk.

        Returns
        -------
        Dict
            Registry dictionary.
        """
        registry_filename = self.registry_filename
        if registry_filename.exists():
            try:
                with open(self.registry_filename, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Could not load registry file {registry_filename}: {e}. Deleting the file."
                )
                self.registry_filename.unlink()
        return {}

    def reset_registry(self):
        """Resets the registry. This will also delete the downloaded files."""
        for k, v in self.registry.items():
            fpath = v.get("filepath", None)
            if fpath:
                pathlib.Path(fpath).unlink(missing_ok=True)
        self.registry_filename.unlink(missing_ok=True)
        self.registry = self.load_registry()

    @validate_call
    def download(
        self,
        url: HttpUrl,
        *,
        target_folder: Optional[pathlib.Path] = None,
        params: Optional[Dict] = None,
        checksum: Optional[str] = None,
        known_hash: Optional[str] = None,
    ) -> pathlib.Path:
        """Returns the downloaded file. Based on an optionally provided checksum
        already downloaded files can be quickly returned.

        Parameters
        ----------
        url : HttpUrl
            URL to download from.
        target_folder : pathlib.Path, optional
            Target folder to save the file.
        params : dict, optional
            Query parameters for the request.
        checksum : str, optional
            SHA256 checksum.
        known_hash : str, optional
            Known hash for verification.

        Returns
        -------
        pathlib.Path
            Path to the downloaded file.
        """
        from .file_io import sanitize_filename

        if checksum and checksum in self.registry:
            logger.debug("Returning already downloaded file")
            filepath = pathlib.Path(self.registry[checksum]["filepath"])
            if filepath.exists():
                return filepath
            self.registry.pop(checksum)

        filename = sanitize_filename(str(url).rsplit("/", 1)[-1])
        if filename == "":
            filename = uuid.uuid4().hex
        assert len(filename) > 0, f"Could not extract filename from URL {url}"
        if target_folder is None:
            file_path = self.file_directory / filename
        else:
            file_path = pathlib.Path(target_folder) / filename
        downloaded_filename = _download_file(
            url, known_hash, target=file_path, params=params
        )
        assert downloaded_filename == file_path, (
            f"Expected {file_path}, got {downloaded_filename}"
        )
        if not checksum:
            checksum = get_checksum(downloaded_filename)
        self.registry[checksum] = {
            "url": str(url),
            "filepath": str(downloaded_filename.absolute().resolve()),
        }
        return downloaded_filename
