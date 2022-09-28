"""Warnings raise by wrapper classes"""


class NoUnitPassedWarning(Warning):
    """Warning raised if no unit was passed during dataset creation"""

    def __init__(self, dataset_name):
        self.message = f'No "units"-attribute for dataset "{dataset_name}"'

    def __str__(self):
        return repr(self.message)


class LongOrStandardNameWarning(Warning):
    """Warning raised if neither a long_name nor a standard_names was passed during dataset creation"""

    def __init__(self, dataset_name):
        self.message = f'No long_name or standard_name given for dataset "{dataset_name}".\n' \
                       f' It is highly recommended to give either of it otherwise file check will fail.'

    def __str__(self):
        return repr(self.message)
