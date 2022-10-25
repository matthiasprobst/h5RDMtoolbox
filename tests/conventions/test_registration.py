import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions.registration import register_hdf_attr
from h5rdmtoolbox.wrapper.core import H5Group


class TestAccessor(unittest.TestCase):

    def test_hdf_attribute(self):
        @register_hdf_attr(H5Group, name='short_name')
        class ShortNameAttribute:
            """Short name attribute"""

            def set(self, value):
                """Set the short_name"""
                self.attrs.create('short_name', value.__str__())

        @register_hdf_attr(H5Group, name=None)
        class shortyname:
            """Shorty name attribute"""

            def set(self, value):
                """Set the shortyname"""
                self.attrs.create('shortyname', value.__str__())

        with h5tbx.H5File() as h5:
            h5.short_name = 'short'
            h5.shortyname = 'shorty'
            self.assertIn('short_name', h5.attrs.keys())
            self.assertIn('shortyname', h5.attrs.keys())
            self.assertEqual(h5.attrs['short_name'], 'short')
            self.assertEqual(h5.attrs['shortyname'], 'shorty')

        with self.assertRaises(AttributeError):
            @register_hdf_attr(H5Group)
            class attrs:
                pass

        @register_hdf_attr(H5Group, overwrite=True)
        class shortyname:

            def set(self, value):
                """Set the shortyname"""
                self.attrs.create('veryshortyname', value.__str__())

        h5tbx.use('cflike')
        with h5tbx.H5File() as h5:
            h5.shortyname = 'shortynew'
            self.assertIn('veryshortyname', h5.attrs.keys())
            self.assertEqual(h5.attrs['veryshortyname'], 'shortynew')
