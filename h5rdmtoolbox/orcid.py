"""ORCID module handling researcher IDs"""
import appdirs
import pathlib
import re
import requests
import warnings
from IPython.display import display, HTML

from typing import Union, List


class KnownOrcids:
    """Class that manages locally stored ORCIDs"""

    def __init__(self):
        self._filename = None
        self._orcids = None

    @property
    def orcids(self) -> List[str]:
        """return list of known orcids"""
        if self._orcids is None:
            self._orcids = self.load()
        return self._orcids

    @property
    def filename(self):
        """return filename of where known orcids"""
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


def get_html_repr(orcid_id: str) -> str:
    """get html representation of orcid_id.
    See https://info.orcid.org/documentation/integration-guide/user-experience-display-guidelines/"""
    oid = ORCID(orcid_id)
    return f"""<a href="{oid}">
<img alt="ORCID logo" src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" width="16" height="16" />
{oid}
</a>"""


ORCID_PATTERN = r'(?:https:\/\/orcid.org\/)?\d{4}-\d{4}-\d{4}-\d{3}[0-9X]'


def is_valid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""

    return not re.match(ORCID_PATTERN, orcid_str) is None


class ORCID(str):
    """ORCID class

    The orcid string is checked only for pattern, not for existence.
    To check for existence, use the exists() method after instantiation.
    """

    def _repr_html_(self):
        return get_html_repr(self)

    def __new__(cls, orcid):
        """Only pattern is checked!
        If existence is to be checked, use exists() method."""
        if not orcid.startswith('https://orcid.org/'):
            orcid = f'https://orcid.org/{orcid}'
        if is_valid_orcid_pattern(orcid):
            return super(ORCID, cls).__new__(cls, orcid)
        raise ValueError(f'Invalid ORCID string: {orcid}')

    def exists(self,
               check_offline: bool = True,
               timeout: Union[int, None] = None,
               raise_error: bool = True) -> bool:
        """Check if it can be found online"""
        headers = {'Accept': 'application/vnd.orcid+json'}
        try:
            response = requests.get(self, headers=headers, timeout=timeout)  # wait 1 sec
        except requests.exceptions.ConnectionError as e:
            if check_offline:
                # no internet connection, look in registered ORCIDs
                warnings.warn('validating the ORCID offline by comparing with registered, known ORCIDs', UserWarning)
                return known_orcids.exists(self)
            if raise_error:
                raise Exception(e) from e
            return False
        if response.status_code == 200:  # 200=OK
            known_orcids.add(self)
            return True
        return False

    def display(self):
        """Display ORCID as HTML. Only works in Jupyter notebooks."""
        display(HTML(get_html_repr(self)))
