import pathlib
import warnings

import yaml

from ._logger import logger

name = 'h5database'

user_config_dir = pathlib.Path.home() / ".config" / __package__.replace('.', '/')
if not user_config_dir.exists():
    user_config_dir.mkdir(parents=True)
user_yaml_filename = user_config_dir / f'{name}.yaml'

config = {
    'datapath': 'data',
    # 'identifier_attr': {'__db_file_type__': 'fan_case'},  # attributes that must be in hdf file to be found
    'hdf5_ext': '.hdf',  # hdf file extension of database hdf files
    'toc_ext': '_toc.hdf',
}

default_dict = config.copy()


def write_default_user_yaml_file(overwrite=False, filename=user_yaml_filename) -> pathlib.Path:
    """Writes the default configuration to a file. Default file location is user_yaml_filename"""
    _filename = pathlib.Path(filename)
    if _filename.exists() and not overwrite:
        warnings.warn('Could not write yaml user file. It already exists and overwrite is set to False')
        return _filename

    logger.info(f'Writing h5database yaml to: {_filename}')
    with open(_filename, 'w') as f:
        yaml.dump(default_dict, f, sort_keys=False)
    return _filename


def read_yaml_file(yaml_filename):
    _yaml_filename = pathlib.Path(yaml_filename)
    with open(_yaml_filename, 'r') as f:
        yaml_config = yaml.safe_load(f)
    return yaml_config


def read_user_yaml_file():
    """Reads the user yaml file and returns the dictionary. Location of the
    yaml file is user_yaml_filename"""
    if not user_yaml_filename.exists():
        write_default_user_yaml_file()
    with open(user_yaml_filename, 'r') as f:
        yaml_config = yaml.safe_load(f)
    return yaml_config


def use(yaml_file):
    _config = read_yaml_file(yaml_file)
    config.update(_config)


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


from .h5repo import H5repo
from .files import H5Files

if not user_yaml_filename.exists():
    write_default_user_yaml_file()

__all__ = ['config', 'user_config_dir', 'set_loglevel', 'H5Files']
