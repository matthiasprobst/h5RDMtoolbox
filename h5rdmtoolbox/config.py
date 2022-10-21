"""config file for wrapper classes"""

from typing import Union

import yaml
from omegaconf import OmegaConf, DictConfig
from ._user import user_dirs

config_yaml_filename = user_dirs['root'] / 'user_config.yaml'

DEFAULT_CONFIG = dict(
    RETURN_XARRAY=True,
    ADVANCED_SHAPE_REPR=True,
    NATURAL_NAMING=True,
    HDF_COMPRESSION='gzip',
    HDF_COMPRESSION_OPTS=5,
    HTML_MAX_STRING_LENGTH=40,  # used for HTML representation of strings (.dump())
    MPL_STYLE='h5rdmtoolbox',  # TODO: seems not to be used
    XARRAY_UNIT_REPR_IN_PLOTS='/',
    REQUIRE_UNITS=True,  # datasets require units
    UREG_FORMAT='C~',
    STANDARD_NAME_TABLE_ATTRIBUTE_NAME='__standard_name_table__',
    CONVENTION='default'
)


def read_user_config() -> DictConfig:
    """Read user configuration"""
    return OmegaConf.load(config_yaml_filename)


def write_user_config():
    """Write config to user direcotr"""
    with open(config_yaml_filename, 'w') as f:
        yaml.dump(OmegaConf.to_yaml(CONFIG), f)


if not config_yaml_filename.exists():
    CONFIG = OmegaConf.create(DEFAULT_CONFIG)
    write_user_config()
else:
    CONFIG = read_user_config()


def set_config_parameter(parameter_name: str, value: Union[float, int, str]):
    """Set value in user configuration"""
    cfg = read_user_config()
    if parameter_name not in cfg:
        raise ValueError(f'Name {parameter_name} not in config')
    CONFIG[parameter_name.upper()] = value
    write_user_config()
