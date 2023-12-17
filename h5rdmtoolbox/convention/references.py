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
    try:
        response = requests.get(url)
    except requests.exceptions.MissingSchema:
        return False
    if response.status_code == 200:
        return True
    return False
