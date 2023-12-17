import appdirs
import configparser
import os
import pathlib
from typing import Union

from h5rdmtoolbox.utils import create_tbx_logger

logger = create_tbx_logger('zenodo')


def _parse_ini_file(zenodo_ini_filename: Union[str, pathlib.Path]):
    if zenodo_ini_filename is None:
        zenodo_ini_filename = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo.ini'
    else:
        zenodo_ini_filename = pathlib.Path(zenodo_ini_filename)
    if not zenodo_ini_filename.exists():
        raise FileNotFoundError(f'File {zenodo_ini_filename} not found.')
    return zenodo_ini_filename


def get_api_token(sandbox: bool,
                  zenodo_ini_filename: Union[str, pathlib.Path] = None):
    """Read the Zenodo API token from the config file."""
    if sandbox:
        env_token = os.environ.get('ZENODO_SANDBOX_API_TOKEN', None)
    else:
        env_token = os.environ.get('ZENODO_API_TOKEN', None)
    if env_token is not None:
        env_token = env_token.strip()
        logger.debug('Took token from environment variable ZENODO_SANDBOX_API_TOKEN.')
        return env_token
    zenodo_ini_filename = _parse_ini_file(zenodo_ini_filename)
    config = configparser.ConfigParser()
    config.read(zenodo_ini_filename)
    if sandbox:
        access_token = config['zenodo:sandbox']['access_token']
    else:
        access_token = config['zenodo']['access_token']
    if not access_token:
        raise ValueError(f'No API token found in {zenodo_ini_filename}. Please verify the correctness of the file '
                         f'{zenodo_ini_filename}. The access_token entry must be in the section [zenodo] or '
                         f'[zenodo:sandbox].')
    return access_token


def set_api_token(sandbox: bool,
                  access_token: str,
                  zenodo_ini_filename: Union[str, pathlib.Path] = None):
    """Write the Zenodo API token to the config file."""
    zenodo_ini_filename = _parse_ini_file(zenodo_ini_filename)
    config = configparser.ConfigParser()
    config.read(zenodo_ini_filename)
    if sandbox:
        section = 'zenodo:sandbox'
    else:
        section = 'zenodo'
    if section not in config:
        config[section] = {}
    config[section]['access_token'] = access_token
    with open(zenodo_ini_filename, 'w') as f:
        config.write(f)
