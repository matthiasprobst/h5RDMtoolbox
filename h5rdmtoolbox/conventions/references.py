import itertools
import json
import re
import requests
from typing import Union, List, Dict

from .standard_attribute import StandardAttribute


class ReferencesError(ValueError):
    """An error associated with the references property"""


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


def parse_ref(str_reference: str) -> Dict:
    """Parse a attrs_str reference into a dictionary

    Parameters
    ----------
    str_reference: str
        The attrs_str reference. Can be an url or a attrs_str representation of a dict

    Returns
    -------
    Dict
        The parsed reference
    """
    if str_reference[0] == '{':
        return json.loads(str_reference)
    return str_reference


class ReferencesAttribute(StandardAttribute):
    """References attribute

    A reference can be an online resource. Currently, only URLs are supported.
    """

    name = 'references'

    def set(self, reference: Union[
        str, List[str],
        Dict, List[Dict]]
            ):
        """Set the reference or multiple references.
        A reference can be a web-source (URL) or a bibtext entry.
        For URLs the package requests is used to validate the URL.

        Parameters
        ----------
        reference: Union[str, List[str], Dict, List[Dict]]
            The reference or list of references to be set.
            A reference can be a web-source (URL) or a bibtext entry.
            For URLs the package requests is used to validate the URL.
        """
        # figure out if the reference is a URL or a bibtex entry
        if not isinstance(reference, (tuple, list)):
            reference = [reference]

        str_references = []
        for r in reference:
            if isinstance(r, str):
                # it's a URL
                if r[-1] != '/':
                    r += '/'
                if not validate_url(r):
                    raise ReferencesError(f'Invalid URL: {r}')
                str_references.append(r)
            else:
                str_references.append(json.dumps(r))

        super().set(','.join(str_references))

    def get(self) -> Union[str, List[str], Dict, List[Dict]]:
        """Read the references from the HDF attribute and return it as an url (str) or
         dictionary (for bibtex) or a list of these."

         .. note:: In case of multiple references, URLs are placed at the beginning of the list followed by the dictionaries.
         """
        attrs_str = super().get()

        if not attrs_str:
            return attrs_str

        # Find all URLs
        # the rsplit is to remove the comma in case there is one as it is unclear how the URL ends
        nested_list_of_urls = [r.split(',') for r in re.findall(r'https?://\S+[/,]', attrs_str)]
        urls = [u for u in list(itertools.chain(*nested_list_of_urls)) if u != '']

        # Find all dictionaries
        dictionaries = re.findall(r'{.*?}', attrs_str)

        list_of_references = [*[u for u in urls if u != ''], *[json.loads(d) for d in dictionaries]]

        if len(list_of_references) == 1:
            return list_of_references[0]
        return tuple(list_of_references)
