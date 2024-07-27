import logging
import pathlib
from typing import Optional, Union

import requests

logger = logging.getLogger('h5rdmtoolbox')


def download_file(file_url,
                  target_folder: Union[str, pathlib.Path] = None,
                  access_token: Optional[str] = None,
                  checksum: Optional[str] = None) -> pathlib.Path:
    from ..utils import DownloadFileManager
    dfm = DownloadFileManager()
    if checksum:
        existing_filename = dfm.get(checksum=checksum, url=file_url)
        if existing_filename:
            return existing_filename

    if target_folder is None:
        from ..user import USER_CACHE_DIR
        target_folder = USER_CACHE_DIR
    else:
        logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        target_folder = pathlib.Path(target_folder)
    target_folder.mkdir(exist_ok=True, parents=True)

    filename = str(file_url).rsplit('/', 1)[-1]
    target_filename = target_folder / filename
    r = requests.get(file_url, params={'access_token': access_token})
    r.raise_for_status()

    try:
        _jdata = r.json()
        if isinstance(_jdata, dict):
            links_content = _jdata.get('links', {}).get('content')
        else:
            links_content = None
    except (requests.exceptions.JSONDecodeError, AttributeError, KeyError) as e:
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

    from ..utils import get_checksum
    checksum = get_checksum(target_filename)
    dfm.add(checksum=checksum, url=file_url, filename=target_filename)
    return target_filename
