"""config file for wrapper classes"""
import warnings
from omegaconf import OmegaConf, DictConfig
from pint_xarray import unit_registry
from typing import Union

from ._user import user_dirs

ureg = unit_registry

user_config_dir = user_dirs['root']
user_config_filename = user_dirs['root'] / 'user_config.yaml'

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
    CONVENTION='default',
    INIT_LOGGER_LEVEL='DEBUG'
)


def read_user_config() -> DictConfig:
    """Read user configuration"""
    return OmegaConf.load(user_config_filename)


def write_user_config(cfg: DictConfig):
    """Write config to user directory"""
    with open(user_config_filename, 'w') as f:
        f.write(OmegaConf.to_yaml(cfg))


if not user_config_filename.exists():
    # generate new config file
    CONFIG = OmegaConf.create(DEFAULT_CONFIG)
    write_user_config(cfg=CONFIG)
else:
    # read from file
    CONFIG = read_user_config()


def check_config(cfg: DictConfig = None,
                 write_to_file: bool = False,
                 remove_wrong: bool = False) -> DictConfig:
    """check configuration.

    Parameters
    ----------
    cfg: DictConfig, optional=None
        The configuration to be checked. If None, it takes
        the current one.
    write_to_file: bool, optional=False
        Update the user file if a change is made
    remove_wrong: bool, optional=False
        Removes wrong configuration entries that are
        not in DEFAULT_CONFIG

    Returns
    -------
    cfg: DictConfig
        The current configuration if now keys were missing or the
        updated configuration now including the missing key-value pairs
    """
    if cfg is None:
        cfg = CONFIG
    if set(DEFAULT_CONFIG).issubset(cfg):
        if remove_wrong:
            for k, v in cfg.items():
                if k not in DEFAULT_CONFIG:
                    warnings.warn('Removing config entry "{k}: {v}"', UserWarning)
                    cfg.pop(k)
            write_user_config(cfg)
        return cfg  # The default configuration is at least a subset of the default one
    # keys in the new config seem to be missing frm the DEFAULT configuration. write a new one!
    warnings.warn('There are entries missing in your configuration. It is updated now. The correct '
                  'entries are kept though.', UserWarning)
    new_cfg = DEFAULT_CONFIG
    for k, v in DEFAULT_CONFIG.items():
        if k in new_cfg:
            new_cfg[k] = v
        else:
            if remove_wrong:
                warnings.warn('Removing config entry "{k}: {v}"', UserWarning)
                new_cfg.pop(k)
    cfg = DictConfig(new_cfg)
    if write_to_file or remove_wrong:
        write_user_config(cfg)
    return cfg


CONFIG = check_config(CONFIG, write_to_file=True, remove_wrong=True)
ureg.default_format = CONFIG.UREG_FORMAT


def set_config_parameter(parameter_name: str, value: Union[float, int, str]):
    """Set value in user configuration"""
    _parameter_name = parameter_name.upper()
    cfg = read_user_config()
    if _parameter_name not in cfg:
        raise ValueError(f'Name "{_parameter_name}" not in config')
    CONFIG[_parameter_name] = value
    write_user_config(CONFIG)
