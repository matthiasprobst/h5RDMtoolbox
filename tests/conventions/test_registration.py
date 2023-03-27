import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions.registration import register_hdf_attr, AbstractUserAttribute
from h5rdmtoolbox.wrapper.core import Group


class TestAccessor(unittest.TestCase):

    def test_hdf_attribute(self):
        with self.assertRaises(AttributeError):
            @register_hdf_attr(Group, name='short_name')
            class ShortNameAttribute:
                """Short name attribute"""

                def set(self, value):
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

        @register_hdf_attr(Group, name=None)
        class shortyname(AbstractUserAttribute):
            """Shorty name attribute"""

            def get(self):
                """Set the short_name"""
                return shortyname.parse(self.attrs.get('short_name', None))

            def delete(self):
                """Delete title attribute"""
                self.attrs.__delitem__('title')

            def set(self, value):
                """Set the shortyname"""
                self.attrs.create('shortyname', value.__str__())

        with h5tbx.File() as h5:
            h5.short_name = 'short'
            h5.shortyname = 'shorty'
            self.assertNotIn('short_name', h5.attrs.keys())
            self.assertIn('shortyname', h5.attrs.keys())
            self.assertEqual(h5.attrs['shortyname'], 'shorty')

        with self.assertRaises(AttributeError):
            @register_hdf_attr(Group)
            class attrs:
                pass

        @register_hdf_attr(Group, overwrite=True)
        class shortyname(AbstractUserAttribute):

            def get(self, value):
                """Set the short_name"""
                return shortyname.parse(self.attrs.get('short_name', None))

            def delete(self):
                """Delete title attribute"""
                self.attrs.__delitem__('title')

            def set(self, value):
                """Set the shortyname"""
                self.attrs.create('veryshortyname', value.__str__())

        h5tbx.use('cflike')
        with h5tbx.File() as h5:
            h5.shortyname = 'shortynew'
            self.assertIn('veryshortyname', h5.attrs.keys())
            self.assertEqual(h5.attrs['veryshortyname'], 'shortynew')
