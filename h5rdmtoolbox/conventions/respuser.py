import re
from typing import List

from .standard_attribute import StandardAttribute

ORCID_PATTERN: str = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'


class OrcidError(ValueError):
    """An error associated with the user property"""


def is_invalid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""
    return re.match(ORCID_PATTERN, orcid_str) is None


class RespUserAttribute(StandardAttribute):
    """RespUser can be one or multiple persons in charge or related to the
    file, group or dataset"""

    name = 'responsible_person'

    def get(self):
        """Get user"""
        user = super().get(src=self.parent, name=self.name)
        return user

    def set(self, orcid):
        """Add user
        Parameters
        ----------
        orcid: str or List[str]
            ORCID of one or many responsible persons.
        Raises
        ------
        TypeError
            If input is not a string or a list of strings
        OrcidError
            If a string is not meeting the ORCID pattern of four times four numbers separated with a dash.
        """
        if not isinstance(orcid, (list, tuple)):
            orcid = [orcid, ]
            for o in orcid:
                if not isinstance(o, str):
                    TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')
                if is_invalid_orcid_pattern(o):
                    raise OrcidError(f'Not an ORCID ID: {o}')
        if len(orcid) == 1:
            super().set(orcid[0])
        super().set(orcid)
