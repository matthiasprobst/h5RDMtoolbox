import re
from typing import Union, List

from . import errors
from ..registration import StandardAttribute

ORCID_PATTERN: str = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'


def is_invalid_orcid_pattern(orcid_str: str) -> bool:
    """Check if the pattern matches. Returns True if no match."""
    return re.match(ORCID_PATTERN, orcid_str) is None


class User(StandardAttribute):
    """User can be one or multiple persons in charge or related to the
    file, group or dataset"""

    name = 'user'


    def getter(self, obj):
        """Get user"""
        user = self.safe_getter(obj)
        return user

    def setter(self, obj, orcid: Union[str, List[str]]):
        """Add user

        Parameters
        ----------
        obj: h5py.Dataset or h5py.Group
            HDF5 object to which the attribute is set. Can be a file, group or dataset, but depends on
            for which object the attribute is registered.
        orcid: str or List[str]
            ORCID of one or many responsible persons.

        Raises
        ------
        TypeError
            If input is not a string or a list of strings
        OrcidError
            If a string is not meeting the ORCID pattern of four times four numbers separated with a dash.
        """
        if not isinstance(orcid, (list, tuple)):
            orcid = [orcid, ]
            for o in orcid:
                if not isinstance(o, str):
                    TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')
                if is_invalid_orcid_pattern(o):
                    raise errors.OrcidError(f'Not an ORCID ID: {o}')
        if len(orcid) == 1:
            obj.attrs.create('user', orcid[0])
        else:
            obj.attrs.create('user', orcid)
