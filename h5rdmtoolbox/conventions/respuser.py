import re
import requests
from typing import List

from .standard_attribute import StandardAttribute

ORCID_PATTERN: str = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'


class OrcidError(ValueError):
    """An error associated with the user property"""


def is_valid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""
    return not re.match(ORCID_PATTERN, orcid_str) is None


def exist(orcid: str) -> bool:
    """Check if the ORCID exists"""
    if not is_valid_orcid_pattern(orcid):
        raise OrcidError(f'Not an ORCID ID: {orcid}')
    url = f'https://orcid.org/{orcid}'
    headers = {'Accept': 'application/vnd.orcid+json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    return False


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
                if not is_valid_orcid_pattern(o):
                    raise OrcidError(f'Not an ORCID ID: {o}')
        if len(orcid) == 1:
            super().set(orcid[0])
        super().set(orcid)
