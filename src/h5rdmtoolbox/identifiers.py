import abc
import re
from typing import Union, List

import requests

from .user import USER_DATA_DIR

KNOWN_ORCID_FILENAME = USER_DATA_DIR / 'known_and_validated_orcids.txt'


class ObjectIdentifier(abc.ABC):
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
    def check_checksum(self) -> bool:
        """Checks the checksum of the identifier"""

    @classmethod
    def check_pattern(cls, identifier: str) -> bool:
        """Check if it fulfills the pattern"""
        if cls.pattern is None:
            raise NotImplementedError('Pattern not implemented')
        return re.match(cls.pattern, identifier) is not None


class ORCID(ObjectIdentifier):
    """https://www.wikidata.org/wiki/Property:P496"""
    pattern = r'^(https:\/\/orcid\.org\/)?(\d{4}-){3}\d{3}(\d|X)$'

    def __init__(self, orcid: str):
        if not orcid.startswith('https://orcid.org/'):
            orcid = f'https://orcid.org/{orcid}'
        self.id = str(orcid)

    @classmethod
    def get_existing_orcids(cls) -> List[str]:
        """Return list of validated ORCIDs. They have been saved
        in a file when they were validated the first time."""
        if not KNOWN_ORCID_FILENAME.exists():
            return []
        with open(KNOWN_ORCID_FILENAME) as f:
            return [l.strip() for l in f.readlines()]

    def check_checksum(self) -> bool:
        """Calculate the check digit for the base digits provided based on
        https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier"""

        # get base digits:
        match = re.search(r'(\d{4}-){3}\d{3}[X\d]$', self.id)
        if match:
            base_digits = match.group()
        else:
            return False  # could not extract base digits
        base_digits = [i for i in ''.join(base_digits.split('-'))]

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
        if str(self) in self.get_existing_orcids():
            return True
        headers = {'Accept': 'application/vnd.orcid+json'}
        try:
            response = requests.get(self, headers=headers, timeout=timeout)  # wait 1 sec
        except requests.exceptions.ConnectionError as e:
            if raise_error:
                raise Exception(e) from e
            return False
        if response.status_code == 200:  # 200=OK
            orcids = self.get_existing_orcids()
            orcids.append(str(self))
            with open(KNOWN_ORCID_FILENAME, 'w') as f:
                f.write('\n'.join(orcids))
            return True
        return False

    def __str__(self):
        return self.id

    def validate(self, check_exists: bool = False) -> bool:
        """Validate ORCID. If check_exists is True, it will also check if it can be found online."""
        self.check_pattern(self.id)

        is_valid = self.check_checksum()

        if check_exists:
            is_valid = self.exists()

        return is_valid

    def _repr_html_(self):
        return f'<a href="{self.id}"><img alt="ORCID logo" ' \
               f'src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" ' \
               f'width="16" height="16" />{self.id}</a>'


class ISBNX(ObjectIdentifier):
    """https://en.wikipedia.org/wiki/International_Standard_Book_Number"""

    def __init__(self, isbn: str):
        self.id = str(isbn)

    def __str__(self):
        return self.id

    def _repr_html_(self):
        return f'<a href="https://www.worldcat.org/isbn/{self.id}">{self.id}</a>'

    @abc.abstractmethod
    def check_checksum(self):
        pass

    def validate(self):
        if not self.check_pattern(self.id):
            return False
        return self.check_checksum()


class ISBN13(ISBNX):
    pattern = r'^(?:ISBN(?:-13)?:? )?(?=[0-9]{13}$|(?=(?:[0-9]+[- ]){4})[- 0-9]{17}$)97[89][- ]?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9]$'

    def check_checksum(self) -> bool:
        """Check pattern
        https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s13.html"""
        chars = list(re.sub("[- ]|^ISBN(?:-1[03])?:?", "", self.id))
        last = chars.pop()
        # Compute the ISBN-13 check digit
        val = sum((x % 2 * 2 + 1) * int(y) for x, y in enumerate(chars))
        check = 10 - (val % 10)
        if check == 10:
            check = "0"
        return str(check) == last


class ISBN10(ISBNX):
    pattern = r'^(?:ISBN(?:-10)?:? )?(?=[0-9X]{10}$|(?=(?:[0-9]+[- ]){3})[- 0-9X]{13}$)[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9X]$'

    def check_checksum(self) -> bool:
        # Compute the ISBN-10 check digit
        chars = list(re.sub("[- ]|^ISBN(?:-1[03])?:?", "", self.id))
        last = chars.pop()
        val = sum((x + 2) * int(y) for x, y in enumerate(reversed(chars)))
        check = 11 - (val % 11)
        if check == 10:
            check = "X"
        elif check == 11:
            check = "0"
        return str(check) == last


# class GND(Identifier):
#     pattern = r'^https://d-nb.info/gnd/\d{8,9}$'
#
#     def __init__(self, gnd: str):
#         self.id = str(gnd)
#
#     def __str__(self):
#         return self.id
#
#     def check_pattern(cls, identifier: str) -> bool:
#         return bool(re.match(cls.pattern, identifier))
#
#     def check_checksum(self) -> bool:
#         """Not implemented yet"""
#         warnings.warn('Checksum not implemented yet')
#         return True
#
#     def _repr_html_(self):
#         return f'<a href="https://d-nb.info/gnd/{self.id}"><img alt="{self.id}" ' \
#                f'src="https://upload.wikimedia.org/wikipedia/commons/8/8e/Logo_Gemeinsame_Normdatei_%28GND%29.svg" ' \
#                f'width="16" height="16" />{self.id}</a>'


class RORID(ObjectIdentifier):
    """https://ror.org/"""
    pattern = r'^(https:\/\/ror\.org\/)?0[a-hj-km-np-tv-z|0-9]{6}[0-9]{2}$'

    def __init__(self, rorid: str):
        self.id = str(rorid)

    def __str__(self):
        if not self.id.startswith('https://ror.org/'):
            return f'https://ror.org/{self.id}'
        return str(self.id)

    def check_checksum(self) -> bool:
        """Checking the checksum not implemented yet"""
        raise NotImplementedError('Checksum not implemented yet')

    def _repr_html_(self):
        return f'<a href="{self.id}"><img alt="ROR logo" ' \
               f'src="https://raw.githubusercontent.com/ror-community/ror-logos/main/ror-icon-rgb.svg" ' \
               f'width="16" height="16" />{self.id}</a>'

    def validate(self):
        """Check if it fulfills the pattern"""
        return self.check_pattern(self.id)


class URN(ObjectIdentifier):
    pattern = r'^urn:[a-z0-9][a-z0-9-]{0,31}:[a-z0-9()+,\-.:=@;$_!*\'%/?#]+$'

    def __init__(self, urn: str):
        self.id = str(urn)

    def __str__(self):
        return self.id

    def check_checksum(self) -> bool:
        return True

    def _repr_html_(self):
        return f'<a href="{self.id}">{self.id}</a>'

    def validate(self):
        return self.check_pattern(self.id)


def from_url(url: str) -> Union[ORCID, None]:
    """Guess identifier from url. If it is not a valid identifier, return None"""
    if url.startswith('https://orcid.org/'):
        return ORCID(url)
    # if url.startswith('https://ror.org/'):
    #     return RORID(url)
    return None
