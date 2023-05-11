import numpy as np

from .core import *
from .validators import Regex, ValidString
from ..standard_name import is_valid_unit


class IsValidUnit(Validator):
    """Valid units. Does this by checking if the unit can be understood by package 'ureg'"""

    def __init__(self, optional: bool = False):
        super().__init__(None, optional=optional, sign='=')

    def __set_message__(self, target: str, success: bool):
        if success:
            self._message = f'"{target}" is unit'
        else:
            self._message = f'"{target}" is not a unit'

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


class IsValidContact(Validator):
    """Validates a contact string by checking if it is one or multiple valid ORCIDs"""

    def __init__(self, optional: bool = False):
        super().__init__(None, optional=optional, sign='=')

    def __set_message__(self, target: str, success: bool):
        if success:
            self._message = f'"{target}" has valid ORCID(s)'
        else:
            self._message = f'"{target}" has not a valid ORCID(s)'

    def validate(self, value) -> bool:
        """validate"""
        from ..contact import exist
        if isinstance(value, np.ndarray):
            orcids = list(value)
        elif isinstance(value, (list, tuple)):
            orcids = value
        elif isinstance(value, str):
            orcids = value.split(',')
        for o in orcids:
            if not exist(o.strip()):
                return False
        return True


TbxLayout = Layout()
TbxLayout['/'].attrs['__h5rdmtoolbox_version__'] = IsValidVersionString()  # e.g. v0.1.0
TbxLayout['/'].attrs['title'] = ValidString()
TbxLayout['/'].attrs['contact'] = IsValidContact()
TbxLayout['*'].specify_dataset(name=...).specify_attrs(dict(standard_name=IsValidStandardName(),
                                                            units=IsValidUnit()))
