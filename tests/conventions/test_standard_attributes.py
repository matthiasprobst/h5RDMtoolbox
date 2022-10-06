"""Testing common funcitonality across all wrapper classs"""

import unittest
from importlib.metadata import metadata

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import errors
from h5rdmtoolbox.conventions import software
from h5rdmtoolbox.conventions.standard_name import StandardNameTable
from h5rdmtoolbox.conventions.standard_name import merge


class TestOptAccessors(unittest.TestCase):

    def test_merge(self):
        registered_snts = StandardNameTable.get_registered()
        new_snt = merge(registered_snts, name='newtable', institution=None,
                        version_number=1, contact='matthias.probst@kit.edu')
        self.assertTrue(new_snt.name, 'newtable')

    def test_software(self):
        meta = metadata('numpy')

        s = software.Software(meta['Name'], version=meta['Version'], url=meta['Home-page'],
                              description=meta['Summary'])

        with h5tbx.H5File() as h5:
            h5.software = s

    def test_long_name(self):
        # is available per default
        with h5tbx.H5File() as h5:
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
        with h5tbx.H5File() as h5:
            h5.attrs['units'] = ' '
            h5.attrs['units'] = 'hallo'

            h5.create_dataset('ds1', shape=(2,), long_name='a long name', units='m**2')

            with self.assertRaises(pint.errors.UndefinedUnitError):
                h5['ds1'].units = 'no unit'

            with self.assertRaises(pint.errors.UndefinedUnitError):
                h5.create_dataset('ds2', shape=(2,), long_name='a long name', units='nounit')

    def test_user(self):
        # not yet protected:
        with h5tbx.H5File() as h5:
            h5.attrs['user'] = '11308429'
            self.assertTrue(h5.attrs['user'], '11308429')
            with self.assertRaises(AttributeError):
                h5.user

        # noinspection PyUnresolvedReferences
        from h5rdmtoolbox.conventions import user
        with h5tbx.H5File() as h5:
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
