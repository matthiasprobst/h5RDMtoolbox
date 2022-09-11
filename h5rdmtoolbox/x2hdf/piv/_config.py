import warnings
from pathlib import Path
from typing import Dict, Union

import yaml

from h5rdmtoolbox.conventions import datetime_str
from ... import config as h5tbx_config

# to use CGNS:
# from ...conventions.cgns import PIVCGNSStandardNameTable
# and change next line:

DEFAULT_TRANSLATION = 'pivview-to-piv-v1'

DEFAULT_CONFIGURATION = {
    'interpolation': False,
    'apply_mask': True,
    'masking': 'slack',  # all disabled and masked data points are set to np.nan
    'time_unit': 's',
    'z_source': 'coord_min',
    'datetime_str': datetime_str,
    'attrs_unit_name': 'units',
    'compression': h5tbx_config.hdf_compression,
    'compression_opts': h5tbx_config.hdf_compression_opts,
    'take_min_nt': True,  # False will fill datasets up with np.NA
    'standardized_name_table_translation': DEFAULT_TRANSLATION,  # convention to use for PIV variables
    'timeAverages': {'compute': False,
                     'use_nc': False},  # reads avg.nc, reyn.nc and rms.nc if available
    'post': {
        'compute': False,
        'grpname': 'post',
        'grpdesc': 'Post processing data',
        'running_mean': {'compute': False,
                         'grpname': 'running_mean',
                         'grpdesc': 'Running mean',
                         'dataset_names': ['u', 'v', ]},
        'running_std': {'compute': False,
                        'grpname': 'running_std',
                        'grpdesc': 'Running standard deviation',
                        'dataset_names': ['u', 'v', ]},
        'velocity_abs_ds_name': 'c',
        'compute_dwdz': False,
    },
}


def read_yaml_file(yaml_filename: Union[str, Path]) -> Dict:
    """Read yaml file and return content asdictionary"""
    _yaml_filename = Path(yaml_filename)
    # with open(_yaml_filename, 'r') as f:
    #     for line in f.readlines():
    #         print(line)
    with open(_yaml_filename, 'r') as f:
        yaml_config = yaml.safe_load(f)
    return yaml_config


def check_yaml_file(yaml_file: Union[Path, Dict]) -> bool:
    """Check keys in yaml file to be a valid piv2hdf configuration"""
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


def write_config(filename: Path, config: Dict, overwrite: bool = False) -> Path:
    """overwrites existing yaml config in user dir with default one and returns path to the file"""
    if filename.exists() and not overwrite:
        print('Could not write yaml user file. It already exists and overwrite is set to False')
        return filename

    print(config)
    with open(filename, 'w') as f:
        yaml.dump(config, f, sort_keys=False)
    return filename

# if __name__ == '__main__':
#     write_config(Path(__file__).parent / 'piv2hdf.yaml', DEFAULT_CONFIGURATION)
