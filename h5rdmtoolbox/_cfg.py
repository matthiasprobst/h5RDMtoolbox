"""package configuration. largely based on xarray's configuration concept. no credits taken!"""
from pint import UnitRegistry
from typing import Dict, Union

ureg = UnitRegistry(force_ndarray_like=True)


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
    'adjusting_plotting_labels': True,
    'xarray_unit_repr_in_plots': 'in',
    'plotting_name_order': ('plot_name', 'long_name', 'standard_name'),
    'require_unit': True,  # datasets require units
    'ureg_format': 'C~',
    'init_logger_level': 'ERROR',
    'dtime_fmt': '%Y%m%d%H%M%S%f',
    'expose_user_prop_to_attrs': True,
    'add_provenance': False,
    'ignore_set_std_attr_err': False,
    'auto_create_h5tbx_version': False,  # automatically creates the group h5rdmtoolbox with the version attribute
    'uuid_name': 'uuid',  # attribute name used for UUIDs
    # if a standard attribute is defined and cannot be retrieved because the value is invalid, ignore it:
    'ignore_get_std_attr_err': False,
    'allow_deleting_standard_attributes': False,
    'ignore_none': False
}

_VALIDATORS = {
    'return_xarray': lambda x: isinstance(x, bool),
    'advanced_shape_repr': lambda x: isinstance(x, bool),
    'natural_naming': lambda x: isinstance(x, bool),
    'hdf_compression': lambda x: isinstance(x, str),
    'hdf_compression_opts': lambda x: isinstance(x, int),
    'xarray_unit_repr_in_plots': lambda x: x in ('/', '()', '(', '[]', '[', '//', 'in'),
    'plotting_name_order': lambda x: isinstance(x, (tuple, list)) and [xx in ('plot_name', 'long_name', 'standard_name')
                                                                       for xx in x],
    'require_unit': lambda x: isinstance(x, bool),
    'ureg_format': lambda x: isinstance(x, str),
    'init_logger_level': lambda x: is_valid_logger_level(x),
    'dtime_fmt': lambda x: isinstance(x, str),
    'expose_user_prop_to_attrs': lambda x: isinstance(x, bool),
    'add_provenance': lambda x: isinstance(x, bool),
    'ignore_set_std_attr_err': lambda x: isinstance(x, bool),
    'ignore_get_std_attr_err': lambda x: isinstance(x, bool),
    'ignore_none': lambda x: isinstance(x, bool)
}


class set_config:
    """Set the configuration parameters."""

    def __init__(self, **kwargs):
        self.old = {}
        for k, v in kwargs.items():
            if k in _VALIDATORS and not _VALIDATORS[k](v):
                raise ValueError(f'Config parameter "{k}" has invalid value: "{v}"')
            if k not in CONFIG:
                raise KeyError(f'Not a configuration key: "{k}"')
            self.old[k] = CONFIG[k]
            if k == 'ureg_format':
                get_ureg().default_format = str(v)
        self._update(kwargs)

    def __enter__(self):
        return

    def __exit__(self, *args, **kwargs):
        self._update(self.old)

    def _update(self, options_dict: Dict):
        CONFIG.update(options_dict)


# set_config = ConfigSetter()


def get_config(key=None):
    """Return the configuration parameters."""
    if key is None:
        return CONFIG
    return CONFIG[key]


def get_ureg() -> UnitRegistry:
    """get unit registry"""
    return ureg


set_config(ureg_format=CONFIG['ureg_format'])
