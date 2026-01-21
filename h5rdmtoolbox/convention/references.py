import requests

from h5rdmtoolbox import __version__

USER_AGENT_HEADER = {
    "User-Agent": f"h5rdmtoolbox/{__version__} (https://github.com/matthiasprobst/h5rdmtoolbox)",
}


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
        response = requests.get(url, headers=USER_AGENT_HEADER)
    except requests.exceptions.MissingSchema:
        return False
    if response.status_code == 200:
        return True
    return False
