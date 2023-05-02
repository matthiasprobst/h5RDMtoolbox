from .core import *
from .validators import Regex, ValidString
from ..standard_name import is_valid_unit


class IsValidUnit(Validator):
    """Valid units. Does this by checking if the unit can be understood by package 'ureg'"""

    def __init__(self, optional: bool = False):
        super().__init__(None, optional=optional, sign='=')

    def __str__(self):
        return "can be understood by package 'ureg'"

    def validate(self, value):
        if self.is_optional:
            return True
        return is_valid_unit(value)


class IsValidStandardName(Regex):
    """Validates a standard name by checking the pattern"""

    def __init__(self, optional: bool = False):
        super().__init__(r'^[a-z][a-z0-9_]*$', optional=optional)

    def __str__(self):
        return "is valid standard name pattern"


class IsValidVersionString(Validator):
    """Validates a version string by using the class packaging.version.Version"""

    def __init__(self, optional: bool = False):
        super().__init__(None, optional=optional, sign='=')

    def __str__(self):
        return "is valid version string"

    def validate(self, value):
        from packaging.version import Version, InvalidVersion
        try:
            Version(value)
            return True
        except InvalidVersion:
            return False


TbxLayout = Layout()
TbxLayout['/'].attrs['__h5rdmtoolbox_version__'] = IsValidVersionString()  # e.g. v0.1.0
TbxLayout['/'].attrs['title'] = ValidString()
TbxLayout['*'].specify_dataset(name=...).specify_attrs(dict(standard_name=IsValidStandardName(),
                                                            units=IsValidUnit()))
