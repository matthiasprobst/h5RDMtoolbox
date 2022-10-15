"""config file for wrapper classes"""

RETURN_XARRAY = True
ADVANCED_SHAPE_REPR = True
NATURAL_NAMING = True,
HDF_COMPRESSION = 'gzip'
HDF_COMPRESSION_OPTS = 5
HTML_MAX_STRING_LENGTH = 40  # used for HTML representation of strings (.dump())
MPL_STYLE = 'h5rdmtoolbox'  # TODO: seems not to be used
XARRAY_UNIT_REPR_IN_PLOTS = '/'
REQUIRE_UNITS = True  # datasets require units
UREG_FORMAT = 'C~'
STANDARD_NAME_TABLE_ATTRIBUTE_NAME = '__standard_name_table__'
