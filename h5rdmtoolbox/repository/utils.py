import logging
import pathlib
import requests
from typing import Optional, Union

from h5rdmtoolbox.utils import generate_temporary_directory

logger = logging.getLogger('h5rdmtoolbox')


def download_file(file_url,
                  target_folder: Union[str, pathlib.Path] = None,
                  access_token: Optional[str] = None) -> pathlib.Path:
    if target_folder is None:
        target_folder = generate_temporary_directory()
    else:
        logger.debug(f'A target folder was specified. Downloading file to this folder: {target_folder}')
        target_folder = pathlib.Path(target_folder)
    target_folder.mkdir(exist_ok=True, parents=True)

    filename = str(file_url).rsplit('/', 1)[-1]
    target_filename = target_folder / filename
    r = requests.get(file_url, params={'access_token': access_token})
    r.raise_for_status()

    try:
        links_content = r.json()['links']['content']
    except (AttributeError, requests.exceptions.JSONDecodeError):
        with open(target_filename, 'wb') as file:
            file.write(r.content)
        links_content = None

    if links_content:
        _content_response = requests.get(links_content,
                                         params={'access_token': access_token})
        if _content_response.ok:
            with open(target_filename, 'wb') as file:
                file.write(_content_response.content)
        else:
            raise requests.HTTPError(f'Could not download file "{filename}" from Zenodo ({file_url}. '
                                     f'Status code: {_content_response.status_code}')
    return target_filename
