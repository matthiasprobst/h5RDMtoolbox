"""All custom error classes of the repo"""
# noinspection PyUnresolvedReferences
from .conventions.cflike.errors import *


class CFLikeImportError(ImportError):
    """ImportError Error"""

    def __init__(self, message=None):
        if message is None:
            message = 'It seems like the dependencies for the cflike package are missing. Consider ' \
                      'installing them. Get all dependencies by calling "pip install h5rdmtoolbox[cflike]"'
        super().__init__(message)
