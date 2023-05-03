import re
import requests
from typing import List

from ._logger import logger
from .standard_attribute import StandardAttribute

ORCID_PATTERN: str = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'


class OrcidError(ValueError):
    """An error associated with the user property"""


def is_valid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""
    return not re.match(ORCID_PATTERN, orcid_str) is None


def exist(orcid: str) -> bool:
    """Check if the ORCID exists by querying the ORCID API.

    Parameters
    ----------
    orcid: str
        ORCID to check. May be an URL or an ORCID ID.

    Returns
    -------
    bool
        True if the ORCID exists, False otherwise.
    """
    if not isinstance(orcid, str):
        raise TypeError(f'Expecting a string representing an ORCID but got {type(orcid)}')
    if orcid.startswith('https://orcid.org/'):
        orcid_id = orcid.split('https://orcid.org/')[1]
        if not is_valid_orcid_pattern(orcid_id):
            logger.error(f'Not an ORCID ID: {orcid_id}')
            return False
        # orcid ID is ok, let the requests package handle the rest
        url = orcid
    else:
        if not is_valid_orcid_pattern(orcid):
            logger.error(f'Not an ORCID ID: {orcid}')
            return False
        url = f'https://orcid.org/{orcid}'
    headers = {'Accept': 'application/vnd.orcid+json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:  # 200=OK
        return True
    return False


class ContactAttribute(StandardAttribute):
    """RespUser can be one or multiple persons in charge or related to the
    file, group or dataset"""

    name = 'contact'

    def get(self):
        """Get user"""
        user = super().get(src=self.parent, name=self.name)
        return user

    def set(self, orcid):
        """Add contact

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
