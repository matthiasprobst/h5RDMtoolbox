from .base import StandardAttributeValidator
import requests


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


class ReferencesValidator(StandardAttributeValidator):

    def __call__(self, references, *args, **kwargs):
        if not isinstance(references, (list, tuple)):
            references = [references, ]
        return all(validate_url(r) for r in references)
