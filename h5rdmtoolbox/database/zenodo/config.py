import appdirs
import configparser
import pathlib

from typing import Union


def get_api_token(sandbox: bool,
                  zenodo_ini_filename: Union[str, pathlib.Path] = None):
    """Read the Zenodo API token from the config file."""
    config = configparser.ConfigParser()
    if zenodo_ini_filename is None:
        zenodo_ini_filename = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'zenodo.ini'
    else:
        zenodo_ini_filename = pathlib.Path(zenodo_ini_filename)
    if not zenodo_ini_filename.exists():
        raise FileNotFoundError(f'File {zenodo_ini_filename} not found.')
    config.read(zenodo_ini_filename)
    if sandbox:
        api_token = config['zenodo:sandbox']['api_token']
    else:
        api_token = config['zenodo']['api_token']
    if not api_token:
        raise ValueError(f'No API token found in {zenodo_ini_filename}. Please verify the correctness of the file '
                         f'{zenodo_ini_filename}. The api_token entry must be in the section [zenodo] or '
                         f'[zenodo:sandbox].')
    return api_token
