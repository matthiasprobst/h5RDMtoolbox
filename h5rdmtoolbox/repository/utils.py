import hashlib
import logging
import pathlib
import uuid
import warnings
from typing import Optional, Union

import requests

logger = logging.getLogger('h5rdmtoolbox')


def download_file(file_url,
                  filename: str,
                  target_folder: Union[str, pathlib.Path] = None,
                  access_token: Optional[str] = None,
                  checksum: Optional[str] = None,
                  checksum_algorithm: Optional[str] = None) -> pathlib.Path:
    logger.debug(f'Attempting to provide file from URL (download or return from cache): {file_url}')
    from ..utils import DownloadFileManager
    dfm = DownloadFileManager()

    existing_filename = dfm.get(checksum=checksum, filename=filename)
    if existing_filename:
        # checksum has been verified before because file is in cache
        return existing_filename

    if target_folder is None:
        from ..user import CACHE_DIR
        target_folder = CACHE_DIR
    else:
        logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        target_folder = pathlib.Path(target_folder)

    if checksum:
        target_filename = target_folder / checksum / filename
    else:
        target_filename = target_folder / f"{uuid.uuid4().hex}" / filename
    if not target_filename.parent.exists():
        target_filename.parent.mkdir(exist_ok=True, parents=True)

    if checksum is not None:
        if checksum_algorithm is None:
            if ":" in checksum:
                checksum_algorithm = checksum.split(":", 1)[0]
            else:
                checksum_algorithm = "md5"  # default

        hasher = None
        if checksum is not None:
            try:
                hasher = hashlib.new(checksum_algorithm)
            except ValueError:
                raise ValueError(f"Unsupported checksum algorithm: {checksum_algorithm}")

        try:
            response = requests.get(file_url, stream=True)
            if response.status_code == 403:
                response = requests.get(file_url, stream=True, params={'access_token': access_token})
        except requests.RequestException as e:
            response = requests.get(file_url, stream=True, params={'access_token': access_token})
        response.raise_for_status()

        chunk_size = 1024  # Define chunk size for download

        with open(target_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    if hasher:
                        hasher.update(chunk)

        assert target_filename.exists(), f"File {target_filename} does not exist."
        logger.debug(f"Download successful.")

        if hasher:
            file_checksum = hasher.hexdigest()
            if file_checksum != checksum:
                print(target_filename)
                warnings.warn(
                    f"Checksum mismatch for {target_filename}: expected {checksum}, got {file_checksum}",
                    RuntimeWarning
                )
                logger.error(
                    f"Checksum mismatch for {target_filename}: expected {checksum}, got {file_checksum}"
                )
                # raise ValueError(
                #     f"Checksum mismatch for {target_filename}: expected {checksum}, got {file_checksum}")
            logger.debug(f"Checksum verification successful.")

        # h = getattr(hashlib, checksum_algorithm)()
        # total = 0
        # with requests.get(file_url, stream=True, params={'access_token': access_token}) as r:
        #     r.raise_for_status()
        #     with open(target_filename, "wb") as f:
        #         for chunk in r.iter_content(1024 * 1024):
        #             if chunk:
        #                 f.write(chunk)
        #                 h.update(chunk)
        #                 total += len(chunk)
        #
        # file_checksum = h.hexdigest().lower()
        # if file_checksum != checksum.lower():
        #     target_filename.unlink(missing_ok=True)
        #     raise ValueError(f'Checksum mismatch for file "{filename}" from Zenodo ({file_url}). '
        #                      f'Expected {checksum_algorithm} checksum: {checksum}, '
        #                      f'but got: {file_checksum}')
    else:
        try:
            r = requests.get(file_url)
        except requests.RequestException as e:
            r = requests.get(file_url, params={'access_token': access_token})

        r.raise_for_status()

        try:
            _jdata = r.json()
            if isinstance(_jdata, dict):
                links_content = _jdata.get('links', {}).get('content')
            else:
                links_content = None
        except (requests.exceptions.JSONDecodeError, AttributeError, KeyError) as _:
            links_content = None

        with open(target_filename, 'wb') as file:
            file.write(r.content)
        if links_content:
            try:
                _content_response = requests.get(links_content)
            except requests.RequestException:
                _content_response = requests.get(links_content, params={'access_token': access_token})
            if _content_response.ok:
                with open(target_filename, 'wb') as file:
                    file.write(_content_response.content)
            else:
                raise requests.HTTPError(f'Could not download file "{filename}" from Zenodo ({file_url}. '
                                         f'Status code: {_content_response.status_code}')

    dfm.add(checksum=checksum,
            url=file_url,
            filepath=target_filename,
            filename=filename)
    return target_filename
