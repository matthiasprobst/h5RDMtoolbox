from .core import *

from ..standard_name import is_valid_unit


class IsValidUnit(Validator):
    """Valid units. Does this by checking if the unit can be understood by package 'ureg'"""

    def __init__(self):
        super().__init__(None, '=')

    def __str__(self):
        return "can be understood by package 'ureg'"

    def __call__(self, value):
        return is_valid_unit(value)


class IsValidStandardName(Regex):
    """Validates a standard name by checking the pattern"""

    def __init__(self):
        super().__init__(r'^[a-z_]+$')

    def __str__(self):
        return "is valid standard name pattern"


class IsValidVersionString(Validator):
    """Validates a version string by using the class packaging.version.Version"""

    def __init__(self):
        super().__init__(None, '=')

    def __str__(self):
        return "is valid version string"

    def __call__(self, value):
        from packaging.version import Version, InvalidVersion
        try:
            Version(value)
            return True
        except InvalidVersion:
            return False


TbxLayout = Layout()
TbxLayout['/'].attrs['__h5rdmtoolbox_version__'] = IsValidVersionString()  # e.g. v0.1.0
TbxLayout['/'].attrs['title'] = ValidString()
TbxLayout['*'].define_dataset(name=..., opt=True).attrs['units'] = IsValidUnit()
TbxLayout['*'].define_dataset(name=..., opt=True).attrs['standard_name'] = IsValidStandardName()
