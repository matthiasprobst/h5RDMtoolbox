import hashlib
import logging
import pathlib
import uuid
from typing import Optional, Union

import requests

logger = logging.getLogger('h5rdmtoolbox')


def download_file(file_url,
                  target_folder: Union[str, pathlib.Path] = None,
                  access_token: Optional[str] = None,
                  checksum: Optional[str] = None,
                  checksum_algorithm: Optional[str] = None) -> pathlib.Path:
    logger.debug(f'Attempting to provide file from URL (download or return from cache): {file_url}')
    from ..utils import DownloadFileManager
    dfm = DownloadFileManager()

    existing_filename = dfm.get(checksum=checksum, url=file_url)
    if existing_filename:
        # checksum has been verified before because file is in cache
        return existing_filename

    if target_folder is None:
        from ..user import USER_CACHE_DIR
        target_folder = USER_CACHE_DIR
    else:
        print(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        target_folder = pathlib.Path(target_folder)
    target_folder.mkdir(exist_ok=True, parents=True)

    guessed_filename_from_url = str(file_url).rsplit('/', 1)[-1]
    suffix = pathlib.Path(guessed_filename_from_url).suffix
    if checksum:
        filename = f'{checksum}{suffix}'
    else:
        filename = f'{uuid.uuid4().hex}{suffix}'
    target_filename = target_folder / filename

    checksum_algorithm = checksum_algorithm or "md5"
    if checksum:
        h = getattr(hashlib, checksum_algorithm)()
        total = 0
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(target_filename, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        h.update(chunk)
                        total += len(chunk)

        file_checksum = h.hexdigest().lower()
        if file_checksum != checksum.lower():
            target_filename.unlink(missing_ok=True)
            raise ValueError(f'Checksum mismatch for file "{filename}" from Zenodo ({file_url}). '
                             f'Expected {checksum_algorithm} checksum: {checksum}, '
                             f'but got: {file_checksum}')
    else:
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
            _content_response = requests.get(links_content, params={'access_token': access_token})
            if _content_response.ok:
                with open(target_filename, 'wb') as file:
                    file.write(_content_response.content)
            else:
                raise requests.HTTPError(f'Could not download file "{filename}" from Zenodo ({file_url}. '
                                         f'Status code: {_content_response.status_code}')

    dfm.add(checksum=checksum, url=file_url, filename=target_filename)
    return target_filename
