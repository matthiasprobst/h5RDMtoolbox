"""All custom error classes of the repo"""


class UnitsError(Exception):
    """Units Error"""
    pass


class StandardizedNameError(Exception):
    """Exception class for error associated with standard name usage"""
    pass


class StandardizedNameTableError(Exception):
    pass


class StandardizedNameTableVersionError(Exception):
    """Incompatible Errors"""
    pass


class EmailError(ValueError):
    """Wrong Email Error"""
    pass