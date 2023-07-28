"""Testing the standard attributes"""
import inspect
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import __author_orcid__
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions import Convention
from h5rdmtoolbox.conventions.standard_attributes import DefaultValue
from h5rdmtoolbox.conventions.standard_attributes.errors import StandardAttributeError


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        self.connected = h5tbx.utils.has_internet_connection()
        # h5tbx.set_config(natural_naming=False)

    def assert_standard_attribute(self, sa):
        self.assertIsInstance(sa.name, str)
        self.assertIsInstance(sa.description, str)
        self.assertIsInstance(sa.is_positional(), bool)
        self.assertIsInstance(sa.target_methods, tuple)
        self.assertIsInstance(sa.validator, list)
        for validator in sa.validator:
            self.assertIsInstance(validator,
                                  h5tbx.conventions.standard_attributes.validators.StandardAttributeValidator)

    def test_standard_attribute_basics(self):
        test = h5tbx.conventions.StandardAttribute('test',
                                                   validator={'$type': 'string'},
                                                   target_methods='create_dataset',
                                                   description='A test',
                                                   )
        self.assertEqual('test', test.name)
        self.assertEqual('A test', test.description)
        self.assertEqual(True, test.is_positional())
        self.assertEqual(('create_dataset',), test.target_methods)
        self.assertEqual(None, test.alternative_standard_attribute)
        self.assert_standard_attribute(test)

    def test_data_source(self):
        h5tbx.use(None)
        data_source = h5tbx.conventions.StandardAttribute('data_source',
                                                          validator={'$in': ['simulation', 'experiment']},
                                                          target_methods='create_dataset',
                                                          description='Data source',
                                                          default_value='simulation'
                                                          )
        self.assertEqual(data_source.name, 'data_source')
        self.assertEqual(data_source.description, 'Data source')
        self.assertEqual(False, data_source.is_positional())
        self.assertEqual(data_source.target_methods, ('create_dataset',))
        self.assertEqual(data_source.default_value, 'simulation')
        self.assert_standard_attribute(data_source)

        cv = h5tbx.conventions.Convention('test_convention', contact=__author_orcid__)
        cv.add(data_source)
        cv.register()
        h5tbx.use(cv.name)
        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, data_source='simulation')
            self.assertEqual(h5['test'].attrs['data_source'], 'simulation')
            self.assertEqual(h5['test'].data_source, 'simulation')
            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('test2', data=1, data_source='invalid')
            h5.create_dataset('test2', data=1)
            self.assertEqual(h5['test2'].attrs['data_source'], 'simulation')
            self.assertEqual(h5['test2'].data_source, 'simulation')

        # self.assertEqual(long_name.validator[0].name, '$regex')

    def test_alternative_standard_attribute(self):
        h5tbx.use(None)
        long_name = h5tbx.conventions.StandardAttribute('long_name',
                                                        validator={'$regex': r'^[a-zA-Z].*(?<!\s)$'},
                                                        target_methods='create_dataset',
                                                        alternative_standard_attribute='comment',
                                                        description='A long name of a dataset',
                                                        )
        comment_name = h5tbx.conventions.StandardAttribute('comment',
                                                           validator={'$regex': r'^[a-zA-Z].*(?<!\s)$',
                                                                      '$minlength': 10},
                                                           target_methods='create_dataset',
                                                           alternative_standard_attribute='long_name',
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

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, comment='A comment which is long enough')
            # print(h5.test.attrs.keys())

        with self.assertRaises(StandardAttributeError):
            with h5tbx.File() as h5:
                h5.create_dataset('test', data=1)
                h5.dumps()

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
                                                          target_methods=('create_dataset', 'create_group', '__init__'),
                                                          description='A reference to a publication in bibtext format',
                                                          default_value='$None'
                                                          )
        url_attr = h5tbx.conventions.StandardAttribute('url',
                                                       validator='$url',
                                                       target_methods=('create_dataset',
                                                                       'create_group',
                                                                       '__init__'),
                                                       description='A reference to an URL',
                                                       default_value='$None'
                                                       )

        reference_attr = h5tbx.conventions.StandardAttribute('references',
                                                             validator='$ref',
                                                             target_methods=('create_dataset',
                                                                             'create_group',
                                                                             '__init__'),
                                                             description='A reference to a publication in bibtext '
                                                                         'format or an URL',
                                                             return_type='sdict',
                                                             default_value='$None'
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
            h5.references
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
            target_methods=("__init__", "create_dataset", "create_group"),
            description='Additional information about the file'
        )
        self.assertEqual(len(comment.validator), 3)

        cv = Convention('test_comment', contact=__author_orcid__)
        cv.add(comment)
        cv.register()

        h5tbx.use(cv.name)

        with h5tbx.File(comment='My comment is long enough') as h5:
            self.assertEqual(h5.comment, 'My comment is long enough')
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

        # units is required. thus default value is EMPTY
        units_attr = h5tbx.conventions.StandardAttribute('units',
                                                         validator='$pintunit',
                                                         target_methods='create_dataset',
                                                         description='A unit of a dataset')
        self.assertEqual(units_attr.default_value, DefaultValue.EMPTY)
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
            with self.assertRaises(ValueError):
                del ds.units
            self.assertEqual(ds.units, 'mm')

    def test_source(self):
        source_attr = h5tbx.conventions.StandardAttribute(
            name='data_base_source',
            validator={'$in': ('experimental',
                               'numerical',
                               'analytical',
                               'synthetically')},
            target_methods=('__init__',
                            'create_dataset',
                            'create_group'),
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

    def test_from_yaml(self):
        convention_filename = tutorial.get_standard_attribute_yaml_filename()
        local_cv = h5tbx.conventions.Convention.from_yaml(convention_filename)
        local_cv.register()
        h5tbx.use(local_cv)
        print(local_cv)

        with h5tbx.File(title='My file',
                        piv_method='multi_grid',
                        seeding_material='dehs',
                        piv_medium='air',
                        contact='https://orcid.org/0000-0001-8729-0482', mode='r+') as h5:
            h5.standard_name_table = 'https://zenodo.org/record/8158764'
