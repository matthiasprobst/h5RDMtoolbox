# # === yaml configuration =====
# import pathlib
#
# from .utils import user_config_dir
#
# DEFAULT_CFG = {'minimum_long_name_length': 1,
#                'advanced_shape_repr': True,
#                'long_name>=dataset_name': False,
#                'minimum_standard_name_length': 4,
#                'list_of_invalid_long_names': ['na', 'n.a.', 'not available', 'notavailable', 'unknown', ''],
#                'NA_unit': 'N.A.',
#                'datetime_str': datetime_str,  # datetime string format used in HDF attributes:
#                'natural_naming': True,
#                'hdf_compression': 'gzip',
#                'hdf_compression_opts': 5,
#                'info_table_spacing': '30,20,8,30',  # string length for each column when text output of __str__()
#                'html_max_string_length': 40,  # used for HTML representation of strings (.dump())
#                'plotting': {'mpl_style': 'h5rdmtoolbox', 'xarray_unit_repr_in_plots': '/'},
#                'completeness_check': {},
#                'completeness': {'check_name_case_sensitivity': True}}
#
#
# def get_configdir():
#     """returns path to configuration file"""
#     return user_yaml_filename.parent
#
#
# def get_config():
#     """returns configuration as dict"""
#     return read_user_yaml_file()
#
#
# def set_config(dictionary):
#     """updates current config with new dictionary and saves it to file"""
#     current_config = get_config()
#     current_config.update(dictionary)
#     with open(user_yaml_filename, 'w') as f:
#         yaml.dump(current_config, f, sort_keys=False)
#     config.update(current_config)
#
#
# if not user_yaml_filename.exists():
#     write_default_user_yaml_file()
#
#
# def clean_user_config_data():
#     """deletes all config folders of all packages"""
#     from .h5database import user_config_dir as h5database_user_config_dir
#     from .x2hdf import user_config_dir as x2hdf_user_config_dir
#     shutil.rmtree(h5database_user_config_dir)
#     shutil.rmtree(x2hdf_user_config_dir)
#     shutil.rmtree(user_config_dir)
#
#
# def write_default_user_yaml_file(overwrite=False):
#     if user_yaml_filename.exists() and not overwrite:
#         print('Could not write yaml user file. It already exists and overwrite is set to False')
#         return
#
#     with open(user_yaml_filename, 'w') as f:
#         yaml.dump(_build_default_config(), f, sort_keys=False)
#
#
# def read_yaml_file(yaml_filename):
#     _yaml_filename = pathlib.Path(yaml_filename)
#     with open(_yaml_filename, 'r') as f:
#         yaml_config = yaml.safe_load(f)
#     return yaml_config
#
#
# def read_user_yaml_file():
#     """Reads the user yaml file and returns the dictionary. Location of the
#     yaml file is h5wrapper.user_yaml_filename"""
#     if not user_yaml_filename.exists():
#         write_default_user_yaml_file()
#     with open(user_yaml_filename, 'r') as f:
#         yaml_config = yaml.safe_load(f)
#     return yaml_config
#
#     mpl_style = yaml_config['plotting']['mpl_style']
#     if '.' in mpl_style:
#         # it is a file. may be relative or absolute
#         if not pathlib.Path(mpl_style).is_absolute():
#             mpl_style = str(user_yaml_filename.parent.joinpath(mpl_style))
#
#     try:
#         matplotlib.style.use(mpl_style)
#     except FileNotFoundError:
#         import warnings
#         warnings.warn(f"could not find style sheet {mpl_style} "
#                       'falling back to "classic"')
#         matplotlib.style.use('classic')
#     return yaml_config
#
#
# def use(yaml_file):
#     _config = read_yaml_file(yaml_file)
#     config.update(_config)
