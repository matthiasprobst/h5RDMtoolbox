"""package configuration. largely based on xarray's configuration concept. no credits taken!"""
from pint import UnitRegistry
from typing import Dict, Union

ureg = None


def is_valid_logger_level(level: Union[str, int]):
    """Check if the logger level is valid."""
    if not isinstance(level, (str, int)):
        # raise TypeError(f'Invalid type for the logger: {type(logger_value)}')
        return False
    if isinstance(level, str):
        return level.lower() in ('error', 'debug', 'critical', 'warning', 'info', 'fatal', 'warning', 'warn')
    # 0: NOTSET, 10: DEBUG, 20: INFO, 30: WARNING, 40: ERROR, 50: CRITICAL
    return level in (0, 10, 20, 30, 40, 50)


CONFIG = {
    'return_xarray': True,
    'advanced_shape_repr': True,
    'natural_naming': True,
    'hdf_compression': None,  # 'gzip',
    'hdf_compression_opts': None,  # 5,
    'ureg_format': 'C~',
    'init_logger_level': 'ERROR',
    'dtime_fmt': '%Y-%m-%dT%H:%M:%S%f',
    'expose_user_prop_to_attrs': True,
    'add_provenance': False,
    'auto_create_h5tbx_version': False,  # automatically creates the group h5rdmtoolbox with the version attribute
    'uuid_name': 'uuid',  # attribute name used for UUIDs
    'ignore_none': False
}

_VALIDATORS = {
    'return_xarray': lambda x: isinstance(x, bool),
    'advanced_shape_repr': lambda x: isinstance(x, bool),
    'natural_naming': lambda x: isinstance(x, bool),
    'hdf_compression': lambda x: x is None or isinstance(x, str),
    'hdf_compression_opts': lambda x: x is None or isinstance(x, int),
    'ureg_format': lambda x: isinstance(x, str),
    'init_logger_level': lambda x: is_valid_logger_level(x),
    'dtime_fmt': lambda x: isinstance(x, str),
    'expose_user_prop_to_attrs': lambda x: isinstance(x, bool),
    'add_provenance': lambda x: isinstance(x, bool),
    'ignore_none': lambda x: isinstance(x, bool)
}


class set_config:
    """Set configuration immediately, optionally restoring it as a context manager.

    All keys and values are validated before configuration is changed. Context
    exit restores previous values, including the shared Pint registry format.
    Compression settings accept ``None`` to restore their uncompressed defaults.
    """

    def __init__(self, **kwargs):
        self.old = {}
        for k, v in kwargs.items():
            if k in _VALIDATORS and not _VALIDATORS[k](v):
                raise ValueError(f'Config parameter "{k}" has invalid value: "{v}"')
            if k not in CONFIG:
                raise KeyError(f'Not a configuration key: "{k}"')
            self.old[k] = CONFIG[k]
        self._update(kwargs)

    def __enter__(self):
        return

    def __exit__(self, *args, **kwargs):
        self._update(self.old)

    def _update(self, options_dict: Dict):
        if 'ureg_format' in options_dict:
            get_ureg().formatter.default_format = options_dict['ureg_format']
        CONFIG.update(options_dict)


# set_config = ConfigSetter()


def get_config(key=None):
    """Return the configuration parameters."""
    if key is None:
        return CONFIG
    return CONFIG[key]


def get_ureg() -> UnitRegistry:
    """get unit registry"""
    global ureg
    if ureg is None:
        ureg = UnitRegistry(force_ndarray_like=True)
        ureg.formatter.default_format = CONFIG["ureg_format"]
    return ureg
