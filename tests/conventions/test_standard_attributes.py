"""Testing common funcitonality across all wrapper classs"""

import json
import unittest
from importlib.metadata import metadata
from typing import Union, Dict, List

from h5rdmtoolbox.conventions.cflike import software, user, errors
from h5rdmtoolbox.conventions.registration import register_standard_attribute
from h5rdmtoolbox.wrapper.cflike import H5File, H5Dataset, H5Group


class TestOptAccessors(unittest.TestCase):

    def setUp(self) -> None:
        @register_standard_attribute(H5Group, name='software', overwrite=True)
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

        @register_standard_attribute(H5Group, name='user', overwrite=True)
        @register_standard_attribute(H5Dataset, name='user', overwrite=True)
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

    def test_software(self):
        meta = metadata('numpy')

        s = software.Software(meta['Name'], version=meta['Version'], url=meta['Home-page'],
                              description=meta['Summary'])

        with H5File() as h5:
            h5.software = s

    def test_long_name(self):
        # is available per default
        with H5File() as h5:
            with self.assertRaises(errors.LongNameError):
                h5.attrs['long_name'] = ' 1234'
            with self.assertRaises(errors.LongNameError):
                h5.attrs['long_name'] = '1234'
            h5.attrs['long_name'] = 'a1234'
            with self.assertRaises(errors.LongNameError):
                h5.create_dataset('ds1', shape=(2,), long_name=' a long name', units='m**2')
            with self.assertRaises(errors.LongNameError):
                h5.create_dataset('ds3', shape=(2,), long_name='123a long name ', units='m**2')

    def test_units(self):
        # is available per default
        import pint
        with H5File() as h5:
            h5.attrs['units'] = ' '
            h5.attrs['units'] = 'hallo'

            h5.create_dataset('ds1', shape=(2,), long_name='a long name', units='m**2')

            with self.assertRaises(pint.errors.UndefinedUnitError):
                h5['ds1'].units = 'no unit'

            with self.assertRaises(pint.errors.UndefinedUnitError):
                h5.create_dataset('ds2', shape=(2,), long_name='a long name', units='nounit')

    def test_user(self):
        with H5File() as h5:
            self.assertEqual(h5.user, None)
            h5.attrs['user'] = '1123-0814-1234-2343'
            self.assertEqual(h5.user, '1123-0814-1234-2343')

        # noinspection PyUnresolvedReferences
        with H5File() as h5:
            with self.assertRaises(errors.OrcidError):
                h5.user = '11308429'
            with self.assertRaises(errors.OrcidError):
                h5.attrs['user'] = '11308429'
            with self.assertRaises(errors.OrcidError):
                h5.user = '123-132-123-123'
            with self.assertRaises(errors.OrcidError):
                h5.user = '1234-1324-1234-1234s'
            h5.user = '1234-1324-1234-1234'
            self.assertTrue(h5.user, '1234-1324-1234-1234')
            h5.user = ['1234-1324-1234-1234', ]
            self.assertTrue(h5.user, ['1234-1324-1234-1234', ])
