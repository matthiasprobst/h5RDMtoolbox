"""All errors associated with the cflike-module
"""


class TitleError(ValueError):
    """An error associated with the title property"""


class ReferencesError(ValueError):
    """An error associated with the references property"""


class UnitsError(Exception):
    """Units Error"""


class StandardNameError(Exception):
    """Exception class for error associated with standard name usage"""


class StandardNameTableError(Exception):
    """Exception class for error associated with standard name usage"""


class StandardNameTableError(Exception):
    """Exception class for StandardName Tables"""


class StandardNameTableVersionError(Exception):
    """Incompatible Errors"""


class EmailError(ValueError):
    """Wrong Email Error"""


class LongNameError(ValueError):
    """An error associated with the long_name property"""
