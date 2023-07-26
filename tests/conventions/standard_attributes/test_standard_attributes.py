"""Testing the standard attributes"""
import inspect
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import __author_orcid__
from h5rdmtoolbox.conventions import Convention
from h5rdmtoolbox.conventions.standard_attributes.errors import StandardAttributeError
from h5rdmtoolbox.conventions.standard_attributes.validators.standard_name import update_datasets


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.connected = h5tbx.utils.has_internet_connection()

    def test_standard_attribute_regex(self):
        h5tbx.use(None)
        long_name = h5tbx.conventions.StandardAttribute('long_name',
                                                        validator={'$regex': r'^[a-zA-Z].*(?<!\s)$'},
                                                        method={
                                                            'create_dataset': {
                                                                'optional': False,
                                                                'alt': 'comment'
                                                            }
                                                        },
                                                        description='A long name of a dataset',
                                                        )
        comment_name = h5tbx.conventions.StandardAttribute('comment',
                                                           validator={'$regex': r'^[a-zA-Z].*(?<!\s)$',
                                                                      '$minlength': 10},
                                                           method={
                                                               'create_dataset': {
                                                                   'optional': False,
                                                                   'alt': 'long_name'
                                                               }
                                                           },
                                                           description='A comment',
                                                           )

        long_name_convention = h5tbx.conventions.Convention('long_name_convention',
                                                            contact=__author_orcid__)
        long_name_convention.add(long_name)
        long_name_convention.add(comment_name)
        long_name_convention.register()
        h5tbx.use(long_name_convention.name)

        self.assertEqual(long_name.name, 'long_name')

        curr_convention = h5tbx.conventions.current_convention
        self.assertEqual(curr_convention.name, 'long_name_convention')
        with self.assertRaises(h5tbx.conventions.errors.ConventionError):
            curr_convention.add(long_name)

        self.assertTrue('long_name' in inspect.signature(h5tbx.Group.create_dataset).parameters.keys())

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, long_name='test')
            self.assertEqual(h5['test'].attrs['long_name'], 'test')

            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('test2', data=1, long_name='123test')

    def test_references(self):
        bibtex_entry = {'article': {'journal': 'Nice Journal',
                                    'comments': 'A comment',
                                    'pages': '12--23',
                                    'month': 'jan',
                                    'abstract': 'This is an abstract. '
                                                'This line should be long enough to test\nmultilines...',
                                    'title': 'An amazing title',
                                    'year': '2013',
                                    'volume': '12',
                                    'ID': 'Cesar2013',
                                    'author': 'Jean Cesar',
                                    'keyword': 'keyword1, keyword2'}
                        }
        url = 'https://h5rdmtoolbox.readthedocs.io/en/latest/'

        bibtex_attr = h5tbx.conventions.StandardAttribute('bibtex',
                                                          validator='$bibtex',
                                                          method={'create_dataset': {'optional': True},
                                                                  'create_group': {'optional': True},
                                                                  '__init__': {'optional': True}},
                                                          description='A reference to a publication in bibtext format',
                                                          )
        url_attr = h5tbx.conventions.StandardAttribute('url',
                                                       validator='$url',
                                                       method={'create_dataset': {'optional': True},
                                                               'create_group': {'optional': True},
                                                               '__init__': {'optional': True}},
                                                       description='A reference to an URL',
                                                       )

        reference_attr = h5tbx.conventions.StandardAttribute('references',
                                                             validator='$ref',
                                                             method={'create_dataset': {'optional': True},
                                                                     'create_group': {'optional': True},
                                                                     '__init__': {'optional': True}},
                                                             description='A reference to a publication in bibtext '
                                                                         'format or an URL',
                                                             return_type='sdict'
                                                             )
        cv = Convention('test_references',
                        contact=__author_orcid__)
        cv.add(bibtex_attr)
        cv.add(url_attr)
        cv.add(reference_attr)

        cv.register()
        h5tbx.use(cv.name)

        for std_attr in ('url', 'bibtex', 'references'):
            self.assertTrue(std_attr in inspect.signature(h5tbx.Group.create_dataset).parameters.keys())
            self.assertTrue(std_attr in inspect.signature(h5tbx.Group.create_group).parameters.keys())
            self.assertTrue(std_attr in inspect.signature(h5tbx.File.__init__).parameters.keys())

        with h5tbx.File() as h5:
            if self.connected:
                h5.url = url
                self.assertEqual(h5.url, url)

            with self.assertRaises(StandardAttributeError):
                h5.url = 'invalid'

            h5.references = bibtex_entry
            self.assertDictEqual(h5.references, bibtex_entry)

            if self.connected:
                h5.references = url
                self.assertEqual(h5.references, url)

                h5.references = (bibtex_entry, url)
                self.assertEqual(h5.references[0], bibtex_entry)
                self.assertEqual(h5.references[1], url)

    def test_comment(self):

        comment = h5tbx.conventions.StandardAttribute(
            name='comment',
            validator={'$regex': r'^[A-Z].*$',
                       '$minlength': 10,
                       '$maxlength': 101},
            method={'__init__': {'optional': True},
                    'create_dataset': {'optional': True},
                    'create_group': {'optional': True}},
            description='Additional information about the file'
        )
        self.assertEqual(len(comment.validator), 3)

        cv = Convention('test_comment', contact=__author_orcid__)
        cv.add(comment)
        cv.register()

        h5tbx.use(cv.name)

        with h5tbx.File() as h5:
            self.assertEqual(h5.comment, None)
            with self.assertRaises(StandardAttributeError):
                h5.comment = ' This is a comment, which starts with a space.'
            with self.assertRaises(StandardAttributeError):
                h5.comment = '9 This is a comment, which starts with a number.'
            with self.assertRaises(StandardAttributeError):
                h5.comment = 'Too short'
            with self.assertRaises(StandardAttributeError):
                h5.comment = 'Too long' * 100

            h5.comment = 'This comment is ok.'
            self.assertEqual(h5.comment, 'This comment is ok.')

    def test_units(self):
        """Test title attribute"""
        units_attr = h5tbx.conventions.StandardAttribute('units',
                                                         validator='$pintunit',
                                                         method={'create_dataset': {'optional': False}},
                                                         description='A unit of a dataset')
        cv = h5tbx.conventions.Convention('ucv',
                                          contact=__author_orcid__)
        cv.add(units_attr)
        cv.register()
        h5tbx.use('ucv')

        with h5tbx.File() as h5:
            ds = h5.create_dataset('test',
                                   data=[1, 2, 3],
                                   units='m')
            with self.assertRaises(StandardAttributeError):
                ds.units = 'test'
            with self.assertRaises(StandardAttributeError):
                ds.units = ('test',)
            self.assertEqual(ds.units, 'm')
            # creat pint unit object:
            ds.units = h5tbx.get_ureg().mm
            self.assertEqual(ds.units, 'mm')
            del ds.units
            self.assertEqual(ds.units, None)

    def test_source(self):
        source_attr = h5tbx.conventions.StandardAttribute(
            name='data_base_source',
            validator={'$in': ('experimental',
                               'numerical',
                               'analytical',
                               'synthetically')},
            method={'__init__': {'optional': True},
                    'create_dataset': {'optional': True},
                    'create_group': {'optional': True}},
            description='Base source of data: experimental, numerical, '
                        'analytical or synthetically'
        )

        cv = Convention('source_convention',
                        contact=__author_orcid__)
        cv.add(source_attr)
        cv.register()

        h5tbx.use(cv.name)

        with h5tbx.File(data_base_source='experimental') as h5:
            self.assertEqual(h5.data_base_source, 'experimental')
            with self.assertRaises(StandardAttributeError):
                h5.data_base_source = 'invlaid'

    def test_standard_name_assignment(self):
        translation_dict = {'u': 'x_velocity'}

        with h5tbx.File() as h5:
            h5.create_dataset('u', data=[1, 2, 3])
            h5.create_dataset('grp/u', data=[1, 2, 3])
            update_datasets(h5, translation_dict, rec=False)
            self.assertEqual(h5['u'].attrs['standard_name'], 'x_velocity')
            self.assertFalse('standard_name' in h5['grp/u'].attrs)
            update_datasets(h5, translation_dict, rec=True)
            self.assertTrue('standard_name' in h5['grp/u'].attrs)
            self.assertEqual(h5['grp/u'].attrs['standard_name'], 'x_velocity')
