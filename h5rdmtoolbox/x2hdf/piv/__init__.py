from ..._user import user_data_dir

if (user_data_dir / 'piv2hdf.yaml').exists():
    from ._config import read_yaml_file

    config = read_yaml_file(user_data_dir / 'piv2hdf.yaml')
else:
    from ._config import DEFAULT_CONFIGURATION

    config = DEFAULT_CONFIGURATION


def use(yaml_file):
    """changes the current global configuration. Passing 'default' set the default values"""
    if yaml_file == 'default':
        from ._config import DEFAULT_CONFIGURATION
        _config = DEFAULT_CONFIGURATION
    else:
        from ._config import read_yaml_file
        _config = read_yaml_file(yaml_file)
    config.update(_config)
