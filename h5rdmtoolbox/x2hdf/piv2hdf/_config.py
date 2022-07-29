import warnings
from pathlib import Path

import yaml

from h5rdmtoolbox.conventions import datetime_str

DEFAULT_CONFIGURATION = {
    'interpolation': False,
    'apply_mask': True,
    'masking': 'slack',  # all disabled and masked data points are set to np.nan
    'time_unit': 's',
    'z_source': 'coord_min',
    'datetime_str': datetime_str,
    'attrs_unit_name': 'units',
    'compression': 'gzip',
    'compression_opts': 5,
    'take_min_nt': True,  # False will fill datasets up with np.NA
    'timeAverages': {'compute': True,
                     'use_nc': False},  # reads avg.nc, reyn.nc and rms.nc if available
    'post': {
        'compute': True,
        'grpname': 'post',
        'grpdesc': 'Post processing data',
        'running_mean': {'compute': True,
                         'grpname': 'running_mean',
                         'grpdesc': 'Running mean',
                         'dataset_names': ['u', 'v', ]},
        'running_std': {'compute': True,
                        'grpname': 'running_std',
                        'grpdesc': 'Running standard deviation',
                        'dataset_names': ['u', 'v', ]},
        'velocity_abs_ds_name': 'c',
        'compute_dwdz': False,
    },
}


def read_yaml_file(yaml_filename):
    _yaml_filename = Path(yaml_filename)
    with open(_yaml_filename, 'r') as f:
        yaml_config = yaml.safe_load(f)
    return yaml_config


def check_yaml_file(yaml_file: Path or dict) -> bool:
    if not isinstance(yaml_file, dict):
        _config = read_yaml_file(yaml_file)
    else:
        _config = yaml_file

    for k in DEFAULT_CONFIGURATION:
        if k not in _config:
            warnings.warn(f'User yaml config entry "{k}" not found in your config.')
            return False
    for k in DEFAULT_CONFIGURATION['timeAverages']:
        if k not in _config['timeAverages']:
            warnings.warn(f'User yaml config entry "timeAverages/{k}" not found in your config.')
            return False
    for k in DEFAULT_CONFIGURATION['post']:
        if k not in _config['post']:
            warnings.warn(f'User yaml config entry "post/{k}" not found in your config.')
            return False
    return True


def write_config(filename, config, overwrite=False) -> Path:
    """overwrites existing yaml config in user dir with default one and returns path to the file"""
    if filename.exists() and not overwrite:
        print('Could not write yaml user file. It already exists and overwrite is set to False')
        return filename

    with open(filename, 'w') as f:
        yaml.dump(config, f, sort_keys=False)
    return filename

# if __name__ == '__main__':
#     write_config(Path(__file__).parent / 'piv2hdf.yaml', DEFAULT_CONFIGURATION)