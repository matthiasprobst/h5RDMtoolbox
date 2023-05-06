import unittest

import h5rdmtoolbox as h5tbx


class TestConventions(unittest.TestCase):

    def test_use(self):
        h5tbx.use('h5py')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.current_convention.name, 'h5py')
        h5tbx.use('tbx')
        self.assertEqual(h5tbx.conventions.current_convention.name, 'tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('tbx2')

    def test_new_convention(self):
        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test title'
            with self.assertRaises(AttributeError):
                title = h5.title
        cv = h5tbx.conventions.Convention('test')
        cv['__init__'].add(attr_cls=h5tbx.conventions.title.TitleAttribute,
                           add_to_method=True,
                           position={'before': 'layout'},
                           optional=True)
        cv.register()
        h5tbx.use('test')
        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test title'
            self.assertEqual(h5.title, 'test title')

    def test_invalid_standard_attribute(self):
        class TitleAttribute:
            """Title attribute"""
            name = 'title'

        cv = h5tbx.conventions.Convention('test')
        with self.assertRaises(TypeError):
            cv['__init__'].add(attr_cls=TitleAttribute, target_cls=h5tbx.File)

        class TitleAttribute:
            """Title attribute"""
            name = 'title'

            def set(self):
                """setter method"""
                return True

        cv = h5tbx.conventions.Convention('test')
        with self.assertRaises(TypeError):
            cv['__init__'].add(attr_cls=TitleAttribute, target_cls=h5tbx.File)

        class TitleAttribute:
            """Title attribute"""
            name = 'title'

            def set(self):
                """setter method"""
                return True

            def get(self):
                """getter method"""
                return True

        cv = h5tbx.conventions.Convention('test')
        with self.assertRaises(TypeError):
            cv['__init__'].add(attr_cls=TitleAttribute, target_cls=h5tbx.File)

        class TitleAttribute(h5tbx.conventions.standard_name.StandardAttribute):
            """Title attribute"""
            name = 'title'

        cv['__init__'].add(attr_cls=TitleAttribute, add_to_method=True)
        # add another time fails
        with self.assertRaises(AttributeError):
            cv['__init__'].add(attr_cls=TitleAttribute, add_to_method=True)
