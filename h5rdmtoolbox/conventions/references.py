import json
import requests
import warnings
from typing import Union, List

from .validator import StandardAttributeValidator


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


BIBTEX_ENTRY_TYPES = ('article',
                      'book',
                      'booklet',
                      'conference',
                      'inbook',
                      'incollection',
                      'inproceedings',)


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


class ReferencesValidator(StandardAttributeValidator):

    def __call__(self, references, *args, **kwargs):
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        if all(validate_reference(r) for r in references):
            if len(references) == 1:
                return parse_dict(references[0])
            return [parse_dict(r) for r in references]


class URLValidator(StandardAttributeValidator):

    def __call__(self, references, *args, **kwargs):
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        if all(validate_url(r) for r in references):
            if len(references) == 1:
                return references[0]
            return references
        raise ValueError(f'Invalid URL: {references}')


def parse_dict(value):
    """Returns a string representation of a dict if value is a dict else passes value through"""
    if isinstance(value, dict):
        return json.dumps(value)
    return value


class BibTeXValidator(StandardAttributeValidator):

    def __call__(self, references, *args, **kwargs) -> List[str]:
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        if all(validate_bibtex(r) for r in references):
            if len(references) == 1:
                return parse_dict(references[0])
            return [parse_dict(r) for r in references]
