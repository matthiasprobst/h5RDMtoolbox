"""Testing common funcitonality across all wrapper classs"""

import json
import unittest
from typing import Union, Dict, List

from h5rdmtoolbox.conventions.cflike import software, user, errors
from h5rdmtoolbox.conventions.cflike.standard_name import StandardName
from h5rdmtoolbox.conventions.registration import register_hdf_attr
from h5rdmtoolbox.wrapper.cflike import H5Dataset, H5Group


class TestStandardName(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""

        @register_hdf_attr(H5Group, name='software', overwrite=True)
        class SoftwareAttribute:
            """property attach to a H5Group"""

            def set(self, sftw: Union[software.Software, Dict]):
                """Get `software` as group attbute"""
                if isinstance(sftw, (tuple, list)):
                    raise TypeError('Software infomration must be provided as dictionary '
                                    f'or object of class Softare, not {type(sftw)}')
                if isinstance(sftw, dict):
                    # init the Software to check for errors
                    self.attrs.create('software', json.dumps(software.Software(**sftw).to_dict()))
                else:
                    self.attrs.create('software', json.dumps(sftw.to_dict()))

            def get(self) -> software.Software:
                """Get `software` from group attbute. The value is expected
                to be a dictionary-string that can be decoded by json.
                However, if it is a real string it is expected that it contains
                name, version url and description separated by a comma.
                """
                raw = self.attrs.get('software', None)
                if raw is None:
                    return software.Software(None, None, None, None)
                if isinstance(raw, dict):
                    return software.Software(**raw)
                try:
                    datadict = json.loads(raw)
                except json.JSONDecodeError:
                    # try figuring out from a string. assuming order and sep=','
                    keys = ('name', 'version', 'url', 'description')
                    datadict = {}
                    raw_split = raw.split(',')
                    n_split = len(raw_split)
                    for i in range(4):
                        if i >= n_split:
                            datadict[keys[i]] = None
                        else:
                            datadict[keys[i]] = raw_split[i].strip()

                return software.Software.from_dict(datadict)

            def delete(self):
                """Delete attribute"""
                self.attrs.__delitem__('standard_name')

        @register_hdf_attr(H5Group, name='user', overwrite=True)
        @register_hdf_attr(H5Dataset, name='user', overwrite=True)
        class UserAttribute:
            """User can be one or multiple persons in charge or related to the
            file, group or dataset"""

            def set(self, orcid: Union[str, List[str]]):
                """Add user
                Parameters
                ----------
                orcid: str or List[str]
                    ORCID of one or many responsible persons.

                Raises
                ------
                TypeError
                    If input is not a string or a list of strings
                OrcidError
                    If a string is not meeting the ORCID pattern of four times four numbers sparated with a dash.
                """
                if not isinstance(orcid, (list, tuple)):
                    orcid = [orcid, ]
                    for o in orcid:
                        if not isinstance(o, str):
                            TypeError(f'Expecting a string or list of strings representing an ORCID but got {type(o)}')
                        if user.is_invalid_orcid_pattern(o):
                            raise errors.OrcidError(f'Not an ORCID ID: {o}')
                if len(orcid) == 1:
                    self.attrs.create('user', orcid[0])
                else:
                    self.attrs.create('user', orcid)

            def get(self) -> Union[str, List[str]]:
                """Get user attribute"""
                return self.attrs.get('user', None)

            def delete(self):
                """Get user attribute"""
                self.attrs.__delitem__('user')

    def test_standard_name(self):
        sn1 = StandardName(name='acc', description=None,
                           canonical_units='m**2/s',
                           snt=None)
        self.assertEqual(sn1.canonical_units, 'm**2/s')
        sn2 = StandardName(name='acc',
                           description=None,
                           canonical_units='m^2/s',
                           snt=None)
        self.assertEqual(sn2.canonical_units, 'm**2/s')
        sn3 = StandardName(name='acc',
                           description=None,
                           canonical_units='m/s',
                           snt=None)
        self.assertEqual(sn2.canonical_units, 'm**2/s')

        self.assertTrue(sn1 == sn2)
        self.assertFalse(sn1 == sn3)
        self.assertTrue(sn1 == 'acc')
        self.assertFalse(sn1 == 'acc2')

        with self.assertRaises(AttributeError):
            self.assertTrue(sn1.check())
        sn4 = StandardName(name='a',
                           description=None,
                           canonical_units='m^2/s',
                           snt=None)
        # self.assertFalse(sn3.check())
