import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions.registration import register_hdf_attr, UserAttr, register_hdf_attribute
from h5rdmtoolbox.wrapper.core import Group, File


class TestAccessor(unittest.TestCase):

    def test_hdf_attribute(self):
        with self.assertRaises(AttributeError):
            @register_hdf_attr(Group, name='short_name')
            class ShortNameAttribute:
                """Short name attribute"""

                def setter(self, value):
                    """Set the short_name"""
                    self.attrs.create('short_name', value.__str__())

        with self.assertRaises(AttributeError):
            @register_hdf_attr(Group, name='short_name')
            class ShortNameAttribute:
                """Short name attribute"""

                def set(self, value):
                    """Set the short_name"""
                    self.attrs.create('short_name', value.__str__())

                def get(self, value):
                    """Set the short_name"""
                    return shortyname.parse(self.attrs.get('short_name', None))

        @register_hdf_attr(Group, name=None, overwrite=True)
        class shortyname(UserAttr):
            """Shorty name attribute"""
            name = 'shortyname'

            def getter(self, obj):
                """Get the short_name and add a !"""
                return self.value(obj) + '!'

        with h5tbx.File() as h5:
            h5.short_name = 'short'
            h5.shortyname = 'shorty'
            self.assertNotIn('short_name', h5.attrs.keys())
            self.assertNotIn('shortyname', h5.attrs.keys())
            # self.assertEqual(h5.attrs['shortyname'], 'shorty')

            # register shortyname to file:
            register_hdf_attribute(shortyname, cls=File)
            h5.shortyname = 'shorty'
            self.assertIn('shortyname', h5.attrs.keys())

        with self.assertRaises(AttributeError):
            @register_hdf_attr(Group)
            class attrs:
                pass
