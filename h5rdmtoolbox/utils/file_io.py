"""File I/O utilities for h5rdmtoolbox."""

import hashlib
import os
import pathlib
import random
import re
import time
from typing import Callable, Optional

import requests

from .. import user
from .._version import __version__

logger = __import__("h5rdmtoolbox", fromlist=["logger"]).logger
RETRY_STATUS = {429, 500, 502, 503, 504}


def get_filesize(filename: pathlib.Path) -> int:
    """Get the size of a file in bytes.

    Parameters
    ----------
    filename : pathlib.Path
        Path to the file.

    Returns
    -------
    int
        Size of the file in bytes.
    """
    from .. import get_ureg

    return os.path.getsize(filename) * get_ureg().byte


def get_checksum(filename: pathlib.Path, hash_func: Callable = hashlib.md5) -> str:
    """Get the checksum of a file. Default hash function is hashlib.md5.

    Parameters
    ----------
    filename : pathlib.Path
        Path to the file.
    hash_func : Callable, optional
        Hash function to use, by default hashlib.md5.

    Returns
    -------
    str
        Hexadecimal checksum string.
    """
    with open(str(filename), "rb") as file:
        return hash_func(file.read()).hexdigest()


def has_internet_connection(timeout: int = 5) -> bool:
    """Figure out whether there's an internet connection.

    Parameters
    ----------
    timeout : int, optional
        Timeout in seconds, by default 5.

    Returns
    -------
    bool
        True if internet connection is available, False otherwise.
    """
    try:
        requests.get("https://git.scc.kit.edu", timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def _request_with_backoff(
    method, url, session=None, max_retries=8, timeout=30, **kwargs
):
    """Perform HTTP request with exponential backoff retry logic.

    Parameters
    ----------
    method : str
        HTTP method (GET, POST, etc.).
    url : str
        URL to request.
    session : requests.Session, optional
        Session to use for requests.
    max_retries : int, optional
        Maximum number of retries, by default 8.
    timeout : int, optional
        Timeout in seconds, by default 30.
    **kwargs
        Additional arguments to pass to requests.

    Returns
    -------
    requests.Response
        Response object.
    """
    r = None
    s = session or requests.Session()
    for attempt in range(max_retries + 1):
        r = s.request(method, url, timeout=timeout, **kwargs)

        if r.status_code not in RETRY_STATUS:
            return r

        retry_after = r.headers.get("Retry-After")
        if retry_after is not None:
            try:
                sleep_s = float(retry_after)
            except ValueError:
                sleep_s = None
        else:
            sleep_s = None

        if sleep_s is None:
            base = min(60.0, 0.5 * (2**attempt))
            sleep_s = random.uniform(0, base)

        if attempt == max_retries:
            return r

        time.sleep(sleep_s)

    return r


def _download_file(
    url,
    known_hash,
    target: Optional[pathlib.Path] = None,
    params: Optional[dict] = None,
) -> pathlib.Path:
    """Download a file from a URL and check its hash.

    Parameters
    ----------
    url : str
        URL to download from.
    known_hash : str, optional
        Expected SHA256 hash of the file.
    target : pathlib.Path, optional
        Target path to save the file.
    params : dict, optional
        Query parameters for the request.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.

    Raises
    ------
    RuntimeError
        If the download fails.
    """
    response = _request_with_backoff("GET", url, params=params, stream=True)
    if response.status_code == 200:
        content = response.content

        calculated_hash = hashlib.sha256(content).hexdigest()
        if known_hash:
            if not calculated_hash == known_hash:
                raise ValueError("File does not match the expected hash")
        else:
            logger.warning(
                "No hash given! This is recommended when downloading files from the web."
            )

        if target:
            fname = target
        else:
            fname = generate_temporary_filename()
        fname.parent.mkdir(parents=True, exist_ok=True)
        with open(fname, "wb") as f:
            f.write(content)

        return fname
    raise RuntimeError(f"Failed to download the file from {url}")


def is_xml_file(filename) -> bool:
    """Check if file is an xml file.

    Parameters
    ----------
    filename : str or pathlib.Path
        Path to the file.

    Returns
    -------
    bool
        True if the file is XML, False otherwise.
    """
    with open(filename, "rb") as file:
        bcontent = file.read()
        content = bcontent.decode("utf-8")
        return re.match(r"^\s*<\?xml", content) is not None


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing illegal characters.

    Parameters
    ----------
    filename : str
        Original filename.

    Returns
    -------
    str
        Sanitized filename.
    """
    illegal_chars = r'[\/:*?"<>|\\]'
    return re.sub(illegal_chars, "_", filename)


def generate_temporary_filename(
    prefix: str = "tmp", suffix: str = "", touch: bool = False
) -> pathlib.Path:
    """Generates a temporary filename in user tmp file directory.

    Parameters
    ----------
    prefix : str, optional
        Prefix string, by default 'tmp'.
    suffix : str, optional
        Suffix including '.', by default ''.
    touch : bool, optional
        If True, creates the empty file, by default False.

    Returns
    -------
    pathlib.Path
        Path to the generated temporary file.
    """
    _filename = user.UserDir["tmp"] / f"{prefix}{next(user._filecounter)}{suffix}"
    while _filename.exists():
        _filename = user.UserDir["tmp"] / f"{prefix}{next(user._filecounter)}{suffix}"
    if touch:
        if _filename.suffix in (".h5", ".hdf", ".hdf5"):
            import h5py

            with h5py.File(_filename, "w"):
                pass
        else:
            with open(_filename, "w"):
                pass
    return _filename


def generate_temporary_directory(prefix: str = "tmp") -> pathlib.Path:
    """Generates a temporary directory in user tmp file directory.

    Parameters
    ----------
    prefix : str, optional
        Prefix string, by default 'tmp'.

    Returns
    -------
    pathlib.Path
        Path to the generated temporary directory.
    """
    _dir = user.UserDir["tmp"] / f"{prefix}{next(user._dircounter)}"
    while _dir.exists():
        _dir = user.UserDir["tmp"] / f"{prefix}{next(user._dircounter)}"
    _dir.mkdir(parents=True)
    return _dir
