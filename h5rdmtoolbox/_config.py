"""Configuration for h5rdmtoolbox
As configuration dictionary, the package omegaconf is used.
It allows type safe configuration and is compatible with dataclasses.
Check it out here: https://omegaconf.readthedocs.io/en/2.1_branch/structured_config.html
"""
import enum
from dataclasses import dataclass
from omegaconf import OmegaConf, DictConfig
from pint_xarray import unit_registry
from typing import Union

from ._user import UserDir

ureg = unit_registry

user_config_dir = UserDir['root']
user_config_filename = UserDir['root'] / 'user_config.yaml'

ureg.default_format = 'C~'


class H5tbxDictConfig(DictConfig):
    """Subclass of DictConfig which updates ureg format when set"""

    def __setitem__(self, key, value):
        if key == 'ureg_format':
            # update ureg format directly
            ureg.default_format = str(value)
        super().__setitem__(key, value)

    def __setattr__(self, key, value):
        if key == 'ureg_format':
            # update ureg format directly
            ureg.default_format = str(value)
        super().__setattr__(key, value)


class UnitPlotRepr(enum.Enum):
    """Representation of value-units separation in plots"""
    NONE = ''
    SLASH = '/'
    CURVED_BRACKETS = '('
    SQUARE_BRACKETS = '['


class HDF5CompressionFilters(enum.Enum):
    """HDF5 compression filters"""
    GZIP = 'gzip'
    LZF = 'lzf'
    SZIP = 'szip'


class UregFormats(enum.Enum):
    """Unit representation formats
    see https://pint.readthedocs.io/en/0.10.1/tutorial.html for available formats"""
    C = 'C~'
    P = 'P~'
    LATEX = 'L~'
    HTML = 'H~'
    ASCII = 'A~'
    NONE = '~'


class RegisteredConventions(enum.Enum):
    DEFAULT = 'default'
    CFLIKE = 'cflike'


@dataclass
class H5tbxConfig:
    """Configuration for h5rdmtoolbox"""
    return_xarray: bool = True
    advanced_shape_repr: bool = True
    natural_naming: bool = True
    hdf_compression: Union[str, HDF5CompressionFilters] = 'gzip'
    hdf_compression_opts: int = 5
    xarray_unit_repr_in_plots: Union[str, UnitPlotRepr] = '/'
    require_unit: bool = True  # datasets require units
    ureg_format: Union[str, UregFormats] = 'C~'
    standard_name_table_attribute_name: str = '__standard_name_table__'
    default_convention: Union[str, RegisteredConventions] = 'default'
    init_logger_level: Union[int, str] = 'INFO'
    dtime_fmt: str = '%Y%m%d%H%M%S%f'


DEFAULT_CONFIG: H5tbxConfig = H5tbxDictConfig(OmegaConf.structured(H5tbxConfig()))
CONFIG: H5tbxConfig = H5tbxDictConfig(OmegaConf.structured(H5tbxConfig()))


def read_user_config() -> H5tbxDictConfig:
    """Read user configuration"""
    if user_config_filename.exists():
        try:
            return H5tbxDictConfig(OmegaConf.structured(H5tbxConfig(**OmegaConf.load(user_config_filename))))
        except TypeError as e:
            TypeError('Most likely an invalid configuration parameter was found in the user configuration file. '
                      f'Please check the file and fix it. File location: {user_config_filename}. '
                      f'Original error: {e}')
    return CONFIG


def write_user_config(cfg: DictConfig) -> H5tbxDictConfig:
    """Write config to user directory"""
    with open(user_config_filename, 'w', encoding="utf-8") as f:
        f.write(OmegaConf.to_yaml(cfg))
    CONFIG = H5tbxDictConfig(OmegaConf.structured(H5tbxConfig(**OmegaConf.load(user_config_filename))))
    return CONFIG


def write_default_config():
    """Write default configuration"""
    write_user_config(DEFAULT_CONFIG)


CONFIG = read_user_config()
