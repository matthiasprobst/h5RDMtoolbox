from .base import StandardAttributeValidator

from ...orcid import ORCID


class ORCIDValidator(StandardAttributeValidator):
    """Validator class, that validates ORCIDs. If an internet
    connection exists, the url is checked, otherwise and if previously
    validated, the ORCID is locally validated."""

    def __call__(self, orcid, *args, **kwargs):
        if not isinstance(orcid, (list, tuple)):
            orcid = [orcid, ]
            for o in orcid:
                if not isinstance(o, str):
                    TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')

                _orcid = ORCID(o)
                if not _orcid.exists():
                    raise ValueError(f'Not an ORCID ID: {o}')
        return True
