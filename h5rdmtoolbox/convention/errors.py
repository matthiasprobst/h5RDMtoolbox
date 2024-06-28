class ConventionError(Exception):
    """Error associated with the convention"""


class ImportConventionError(Exception):
    pass


class ConventionNotFound(Exception):
    """Raised when a convention is not found."""


class UnitsError(Exception):
    """Units Error"""


class StandardAttributeError(Exception):
    """Error during standard attribute handling"""


class StandardAttributeValidationError(Exception):
    """Error during validator calls"""


class StandardAttributeValidationReadError(Exception):
    """Error during reading of HDF5 attribute by a validator"""


class TransformationFunctionError(Exception):
    """Error with a transformation function"""


class StandardNameError(Exception):
    """Exception class for error associated with standard name usage"""


class AffixKeyError(Exception):
    """Exception class for error associated with standard name usage"""


class StandardNameTableError(Exception):
    """Exception class for StandardName Tables"""

class StandardAttributeValidationWarning(Warning):
    """Warning during reading of HDF5 attribute by a validator"""