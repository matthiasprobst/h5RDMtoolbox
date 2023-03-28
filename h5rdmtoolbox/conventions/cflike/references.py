import requests
from typing import Union, List

from .errors import ReferencesError
from ..registration import UserAttr


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


class ReferencesAttribute(UserAttr):
    """References attribute

    A reference can be an online resource. Currently, only URLs are supported.
    """

    name = 'references'

    def setter(self, obj, value: Union[str, List[str]]):
        """Set the reference or multiple references"""
        if isinstance(value, str):
            references = value.split(',')
        else:
            references = value
        for ref in references:
            if not validate_url(ref):
                raise ReferencesError(f'Invalid URL: {ref}')

        if len(references) == 1:
            obj.attrs.create(self.name, references[0])
        else:
            obj.attrs.create(self.name, ','.join(references))

    def getter(self, obj):
        """Get references attribute"""
        value = self.safe_getter(obj)

        if value:
            list_of_references = value.split(',')
            if len(list_of_references) == 1:
                return list_of_references[0]
            return tuple(list_of_references)
        return value
