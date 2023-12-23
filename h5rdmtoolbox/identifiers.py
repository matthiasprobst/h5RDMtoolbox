import abc
import appdirs
import pathlib
import re
import requests
from typing import Iterable
from typing import Union, List


class Identifier(abc.ABC):
    """Abstract base class for identifiers"""

    wikidata: str = None  # url to wikidata page if exists
    pattern: str = None  # regex pattern to check if identifier is valid

    @abc.abstractmethod
    def __str__(self):
        """return string representation of identifier"""

    @abc.abstractmethod
    def _repr_html_(self):
        """return HTML representation of identifier"""

    @abc.abstractmethod
    def validate(self, check_online: bool = False) -> bool:
        """validate identifier. Does not check if it can be found online!"""

    @abc.abstractmethod
    def exists(self,
               timeout: Union[int, None] = None,
               raise_error: bool = True) -> bool:
        """Check if it can be found online"""

    @abc.abstractmethod
    def check_checksum(self, base_digits: Iterable[int]) -> bool:
        """Checks the checksum of the identifier"""

    @classmethod
    def check_pattern(cls, orcid):
        """Check if it fulfills the pattern"""
        if cls.pattern is None:
            raise NotImplementedError('Pattern not implemented')
        return re.match(cls.pattern, orcid) is None


class Orcid(Identifier):
    """https://www.wikidata.org/wiki/Property:P496"""
    known_orcid_filename = pathlib.Path(appdirs.user_data_dir('h5rdmtoolbox')) / 'known_and_validated_orcids.txt'
    pattern = r'^(https:\/\/orcid\.org\/)?(\d{4}-){3}\d{3}(\d|X)$'

    def __init__(self, orcid: str):
        if not orcid.startswith('https://orcid.org/'):
            orcid = f'https://orcid.org/{orcid}'
        self.id = str(orcid)

    def get_validated_orcids(self) -> List[str]:
        """Return list of validated ORCIDs. They have been saved
        in a file when they were validated the first time."""

        if not self.known_orcid_filename.exists():
            return []
        with open(self.known_orcid_filename) as f:
            return [l.strip() for l in f.readlines()]

    @staticmethod
    def check_checksum(base_digits: Iterable[str]) -> bool:
        """Calculate the check digit for the base digits provided based on
        https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier"""

        if base_digits[-1] == 'X':
            checksum = 10
        else:
            checksum = int(base_digits[-1])

        total = 0
        for digit in base_digits[:-1]:
            total = (total + int(digit)) * 2

        remainder = total % 11
        result = (12 - remainder) % 11

        return result == checksum

    def exists(self,
               timeout: Union[int, None] = None,
               raise_error: bool = True) -> bool:
        """Check if it can be found online or in known ORCIDs file"""
        # small hack: we saved already validated orcids in a file,
        # so we don't have to check them again
        if str(self) in self.get_validated_orcids():
            return True
        headers = {'Accept': 'application/vnd.orcid+json'}
        try:
            response = requests.get(self, headers=headers, timeout=timeout)  # wait 1 sec
        except requests.exceptions.ConnectionError as e:
            if raise_error:
                raise Exception(e) from e
            return False
        if response.status_code == 200:  # 200=OK
            orcids = self.get_validated_orcids()
            orcids.append(str(self))
            with open(self.known_orcid_filename, 'w') as f:
                f.write('\n'.join(orcids))
            return True
        return False

    def __str__(self):
        return self.id

    def validate(self, check_exists: bool = False) -> bool:
        id = self.id
        self.check_pattern(id)

        # get base digits:
        match = re.search(r'(\d{4}-){3}\d{3}[X\d]$', id)
        if match:
            base_digits = match.group()
        else:
            return False  # could not extract base digits
        is_valid = self.check_checksum([i for i in ''.join(base_digits.split('-'))])

        if check_exists:
            is_valid = self.exists()

        return is_valid

    def _repr_html_(self):
        return f'<a href="{self.id}"><img alt="ORCID logo" ' \
               f'src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" ' \
               f'width="16" height="16" />{self.id}</a>'


def from_url(url: str) -> Union[Orcid, None]:
    """Guess identifier from url. If it is not a valid identifier, return None"""
    if url.startswith('https://orcid.org/'):
        return Orcid(url)
    return None
