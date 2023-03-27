import requests
from typing import Union, List

from .errors import ReferencesError
from ..registration import AbstractUserAttribute


def validate_url(url: str) -> bool:
    """Validate URL

    Parameters
    ----------
    url: str
        URL to be validated

    Returns
    -------
    bool
        True if URL
    """
    response = requests.get(url)
    if response.status_code == 200:
        return True
    return False


class ReferencesAttribute(AbstractUserAttribute):
    """References attribute

    A reference can be an online resource. Currently, only URLs are supported.
    """

    def set(self, value: Union[str, List[str]]):
        """Set the reference or multiple references"""
        if isinstance(value, str):
            references = value.split(',')
        else:
            references = value
        for ref in references:
            if not validate_url(ref):
                raise ReferencesError(f'Invalid URL: {ref}')

        if len(references) == 1:
            self.attrs.create('references', references[0])
        else:
            self.attrs.create('references', ','.join(references))

    @staticmethod
    def parse(value, obj=None) -> Union[str, tuple, None]:
        """Parse references attribute"""
        if value:
            list_of_references = value.split(',')
            if len(list_of_references) == 1:
                return list_of_references[0]
            return tuple(list_of_references)
        return value

    def get(self):
        """Get references attribute"""
        return ReferencesAttribute.parse(self.attrs.get('references', None))

    def delete(self):
        """Delete title attribute"""
        self.attrs.__delitem__('title')
