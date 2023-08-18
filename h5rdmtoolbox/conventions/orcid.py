"""Validator module for use of ORCIDs"""

from typing import Union, List

from h5rdmtoolbox.orcid import ORCID
from .validator import StandardAttributeValidator


class ORCIDValidator(StandardAttributeValidator):
    """Validator class, that validates ORCIDs. If an internet
    connection exists, the url is checked, otherwise and if previously
    validated, the ORCID is locally validated."""

    def __call__(self, orcid, *args, **kwargs) -> Union[str, List[str]]:
        if not isinstance(orcid, (list, tuple)):
            orcid = [orcid, ]
            for o in orcid:
                if not isinstance(o, str):
                    raise TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')

                _orcid = ORCID(o)
                if not _orcid.exists():
                    raise ValueError(f'Not an ORCID ID: {o}')
        if len(orcid) == 1:
            return orcid[0]
        return orcid
