import appdirs
import pathlib
import re
import requests
import warnings
from typing import List

from ._logger import logger
from .standard_attribute import StandardAttribute

ORCID_PATTERN: str = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'

CHECK_OFFLINE = True
REQUEST_TIMEOUT = None


class OrcidError(ValueError):
    """An error associated with the user property"""


def is_valid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""
    return not re.match(ORCID_PATTERN, orcid_str) is None


class KnownOrcids:

    def __init__(self):
        self._filename = None
        self._orcids = None

    @property
    def orcids(self):
        if self._orcids is None:
            self._orcids = self.load()
        return self._orcids

    @property
    def filename(self):
        if self._filename is None:
            root_dir = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox'))
            self._filename = root_dir / 'known_and_validated_orcids.txt'
        return self._filename

    def load(self):
        """load list from file"""
        if not self.filename.exists():
            self._orcids = []
        else:
            with open(self.filename) as f:
                self._orcids = [l.strip() for l in f.readlines()]
        return self._orcids

    def save(self):
        """save the file"""
        with open(self.filename, 'w') as f:
            f.writelines('\n'.join(self.orcids))

    def add(self, orcid):
        """add valid orcid to known list if not already exists"""
        if not self.exists(orcid):
            self.orcids.append(orcid)
            self.save()

    def exists(self, orcid) -> bool:
        """check if orcid is known (has been validated yet)"""
        return orcid in self.orcids


known_orcids = KnownOrcids()


def exist(orcid: str) -> bool:
    """Check if the ORCID exists by querying the ORCID API.
    If not internet connection exist and the orcid is not listed in
    known ORCIDs, only the pattern is checked.

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
            logger.debug(f'Not an ORCID ID: {orcid_id}')
            return False
        # orcid ID is ok, let the requests package handle the rest
        url = orcid
    else:
        orcid_id = orcid
        if not is_valid_orcid_pattern(orcid):
            logger.debug(f'Not an ORCID ID: {orcid}')
            return False
        url = f'https://orcid.org/{orcid}'
    headers = {'Accept': 'application/vnd.orcid+json'}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)  # wait 1 sec
    except requests.exceptions.ConnectionError as e:
        if CHECK_OFFLINE:
            # no internet connection, look in registered ORCIDs
            warnings.warn('validating the ORCID offline by comparing with registered, known ORCIDs', UserWarning)
            return known_orcids.exists(orcid_id)
        raise Exception(e)
    if response.status_code == 200:  # 200=OK
        known_orcids.add(orcid_id)
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
                if not exist(o):
                    raise OrcidError(f'Not an ORCID ID: {o}')
        if len(orcid) == 1:
            super().set(orcid[0])
        super().set(orcid)
