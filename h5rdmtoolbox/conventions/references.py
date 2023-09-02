import json
import requests
import warnings
from typing import Union

BIBTEX_ENTRY_TYPES = ('article',
                      'book',
                      'booklet',
                      'conference',
                      'inbook',
                      'incollection',
                      'inproceedings',)


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
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        return False
    if response.status_code == 200:
        return True
    return False


def validate_bibtex(bibtex: Union[str, dict]) -> bool:
    """Validate BibTeX entry based on the mandatory keys.

    Example entry:
    bibtex = {'article': {'title': 'Title',
                            'author': 'Author',
                            'year': '2020',
                            ...}
                            }
    """
    if isinstance(bibtex, str):
        bibtex = json.loads(bibtex)
    mandatory_keys = ['title', 'author', 'year']
    for entry_type, fields in bibtex.items():
        if entry_type[0] == '@':
            entry_type = entry_type[1:]
        if entry_type.lower() not in BIBTEX_ENTRY_TYPES:
            warnings.warn(f'Invalid BibTeX entry type: {entry_type}. Expected types: {BIBTEX_ENTRY_TYPES}')
            return False
        if not all(k in fields for k in mandatory_keys):
            return False
    return True


def validate_reference(reference: str) -> bool:
    if isinstance(reference, dict):
        return validate_bibtex(reference)
    if isinstance(reference, str) and reference[0] == '{':
        return validate_bibtex(json.loads(reference))
    return validate_url(reference)
