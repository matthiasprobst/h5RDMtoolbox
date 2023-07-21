"""Testing the standard attributes"""
import inspect
import requests
import unittest
import warnings
from pint.errors import UndefinedUnitError

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import conventions, tutorial
from h5rdmtoolbox.conventions.layout.tbx import IsValidVersionString, IsValidUnit
from h5rdmtoolbox.conventions.layout.tbx import is_valid_unit
from h5rdmtoolbox.conventions.standard_attributes import StandardNameTable, StandardName
from h5rdmtoolbox.conventions.standard_attributes.errors import StandardAttributeError, StandardNameError, UnitsError
from h5rdmtoolbox.conventions.standard_attributes.utils import check_url
from h5rdmtoolbox.conventions.standard_attributes.validators.standard_name import update_datasets


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

    def test_standard_attribute_regex(self):
        h5tbx.use(None)
        long_name = h5tbx.conventions.StandardAttribute('long_name',
                                                        validator={'$regex': '^[a-zA-Z].*(?<!\s)$'},
                                                        method={'create_dataset': {'optional': True}},
                                                        description='A long name of a dataset',
                                                        )

        long_name_convention = h5tbx.conventions.Convention('long_name_convention')
        long_name_convention.add(long_name)
        long_name_convention.register()
        h5tbx.use(long_name_convention.name)

        self.assertEqual(long_name.name, 'long_name')

        curr_convention = h5tbx.conventions.current_convention
        self.assertEqual(curr_convention.name, 'long_name_convention')
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
        cv = conventions.Convention('test_references')
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

    def test_standard_name_convention(self):
        h5tbx.use(None)
        units_attr = h5tbx.conventions.StandardAttribute('units',
                                                         validator='$pintunit',
                                                         method={'create_dataset': {'optional': False}},
                                                         description='A unit of a dataset',
                                                         )
        standard_name = h5tbx.conventions.StandardAttribute('standard_name',
                                                            validator='$standard_name',
                                                            method={'create_dataset': {'optional': False}},
                                                            description='A standard name of a dataset',
                                                            )
        snt = h5tbx.conventions.StandardAttribute('standard_name_table',
                                                  validator='$standard_name_table',
                                                  method={'__init__': {'optional': True, }},
                                                  default_value='https://zenodo.org/record/8158764',
                                                  description='A standard name table',
                                                  )

        cv = conventions.Convention('test_standard_name')
        cv.add(units_attr)
        cv.add(standard_name)
        cv.add(snt)
        cv.register()
        h5tbx.use(cv.name)

        self.assertIn('standard_name', inspect.signature(h5tbx.Group.create_dataset).parameters.keys())
        self.assertIn('units', inspect.signature(h5tbx.Group.create_dataset).parameters.keys())
        self.assertIn('standard_name_table', inspect.signature(h5tbx.File.__init__).parameters.keys())

        if self.connected:
            with h5tbx.File(standard_name_table='https://zenodo.org/record/8158764') as h5:
                print(h5.standard_name_table)

                h5.create_dataset('test', data=1, standard_name='x_velocity', units='m/s')
                print(h5['test'])

    def test_is_valid_unit(self):
        self.assertTrue(is_valid_unit('m/s'))
        self.assertTrue(is_valid_unit('1 m/s'))
        self.assertTrue(is_valid_unit('kg m/s^-1'))
        self.assertFalse(is_valid_unit('kg m/s-1'))
        self.assertFalse(is_valid_unit('kgm/s-1'))
        self.assertTrue(is_valid_unit('pixel'))

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

        cv = conventions.Convention('test_comment')
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
        cv = h5tbx.conventions.Convention('ucv')
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

        cv = conventions.Convention('source_convention')
        cv.add(source_attr)
        cv.register()

        h5tbx.use(cv.name)

        with h5tbx.File(data_base_source='experimental') as h5:
            self.assertEqual(h5.data_base_source, 'experimental')
            with self.assertRaises(StandardAttributeError):
                h5.data_base_source = 'invlaid'

    def test_standard_name(self):
        with self.assertRaises(StandardNameError):
            sn_fail = StandardName(name='', units='m')

        with self.assertRaises(StandardNameError):
            StandardName(name=' x', units='m', description='a description')

        with self.assertRaises(StandardNameError):
            sn_fail = StandardName(name='x ', units='m', description='a description')

        sn1 = StandardName(name='acc',
                           description='a description',
                           units='m**2/s')
        self.assertEqual(sn1.units, h5tbx.get_ureg().Unit('m**2/s'))

        with self.assertRaises(StandardNameError):
            tutorial.get_standard_name_table()['z_coord']

    def test_validversion(self):
        self.assertTrue(IsValidVersionString()('v0.1.0'))
        self.assertFalse(IsValidVersionString()('a.b.c'))

    def test_validunit(self):
        self.assertTrue(IsValidUnit()('m/s'))
        self.assertTrue(IsValidUnit()('1 m/s'))
        self.assertFalse(IsValidUnit()('hello/world'))

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

    try:
        import pooch
        run_tests = True
    except ImportError:
        run_tests = False
        warnings.warn(f'Cannot test certain things about standard name table because "pooch" is not installed.')

    if run_tests:
        def test_StandardNameTableFromYaml(self):
            table = StandardNameTable.from_yaml(tutorial.testdir / 'sntable.yml')
            self.assertEqual(table.name, 'test')
            self.assertEqual(table.version_number, 1)
            self.assertEqual(table.institution, 'ITS')
            self.assertEqual(table.contact, 'https://orcid.org/0000-0001-8729-0482')
            self.assertEqual(table.valid_characters, '')
            self.assertEqual(table.pattern, '')
            # table.rename('mean_particle_diameter', 'mean_particle_diameter2')
            # self.assertFalse('mean_particle_diameter' in table)
            # self.assertTrue('mean_particle_diameter2' in table)

            # self.assertListEqual(table.names, ['synthetic_particle_image', 'mean_particle_diameter2'])

            table.table = {'synthetic_particle_image': {
                'units': 'pixel',
            },
                'mean_particle_diameter2': {
                    'description': 'The mean particle diameter of an image particle. The diameter is defined as the 2 sigma with of the gaussian intensity profile of the particle image.',
                    'units': 'pixel'}
            }
            # with self.assertRaises(tbx.DescriptionMissing):
            #     table.check_table()

            table.table = {
                'synthetic_particle_image': {
                    'units': 'pixel',
                    'description': 'Synthetic particle image velocimetry image containing image particles of a single '
                                   'synthetic recording.'},
                'mean_particle_diameter2': {
                    'description': 'The mean particle diameter of an image particle. The diameter is defined as the 2 '
                                   'sigma with of the gaussian intensity profile of the particle image.',
                    'units': 'pixel'}
            }

            table.update(a_velocity={
                'description': 'velocity in a direction',
                'units': 'm/s'
            })
            self.assertEqual(table['a_velocity'].description, 'velocity in a direction')
            from h5rdmtoolbox import get_ureg
            self.assertEqual(table['a_velocity'].units, get_ureg()('m/s'))

        def test_StandardNameTableVersion(self):
            versions = [
                ("v79", True),
                ("v1.2", True),
                ("v2.3a", True),
                ("v3.0dev", True),
                ("v3.0.1dev", False),
                ("v4.5rc", True),
                ("v4.5.6rc", False),
                ("v7.8b", True),
                ("v10", True),
                ("invalid_version", False),
            ]
            for version, valid in versions:
                if valid:
                    self.assertEqual(StandardNameTable.validate_version(version), version)
                else:
                    with self.assertRaises(ValueError):
                        StandardNameTable.validate_version(version)

        def test_StandardNameTableFromWeb(self):
            cf = StandardNameTable.from_web(
                url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml',
                name='standard_name_table')
            self.assertEqual(cf.name, 'standard_name_table')
            self.assertEqual(cf.versionname, 'standard_name_table-v79')
            if self.connected:
                self.assertTrue(check_url(cf.url))
                self.assertFalse(check_url(cf.url + '123'))

            if self.connected:
                opencefa = StandardNameTable.from_gitlab(url='https://git.scc.kit.edu',
                                                         file_path='open_centrifugal_fan_database-v1.yaml',
                                                         project_id='35443',
                                                         ref_name='main')
                self.assertEqual(opencefa.name, 'open_centrifugal_fan_database')
                self.assertEqual(opencefa.versionname, 'open_centrifugal_fan_database-v1')

    def test_StandardNameTableFromYaml_special(self):
        table = StandardNameTable.from_yaml(tutorial.testdir / 'sntable_with_split.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version_number, 1)
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertDictEqual(
            table.table,
            {
                'synthetic_particle_image': {
                    'units': 'counts',
                    'description':
                        'Synthetic particle image velocimetry image containing image particles '
                        'of a single synthetic recording.'
                },
                'mean_particle_diameter': {
                    'units': 'pixel',
                    'description':
                        'The mean particle diameter of an image particle. The diameter is defined '
                        'as the 2 sigma with of the gaussian intensity profile of the particle image.'
                }
            })
        self.assertDictEqual(table.alias, {'particle_image': 'synthetic_particle_image'}
                             )
        self.assertTrue(table.check_name('synthetic_particle_image'))
        self.assertFalse(table.check_name('particle_image'))
        self.assertIsInstance(table['synthetic_particle_image'], StandardName)

    # def test_merge(self):
    #     registered_snts = StandardNameTable.get_registered()
    #     new_snt = tbx.merge(registered_snts, name='newtable', institution=None,
    #                         version_number=1, contact='https://orcid.org/0000-0001-8729-0482')
    #     self.assertTrue(new_snt.name, 'newtable')

    def test_empty_SNT(self):
        snt = StandardNameTable(name='test_snt',
                                table={},
                                version='v1.0dev',
                                institution='my_institution',
                                contact='https://orcid.org/0000-0001-8729-0482')
        self.assertIsInstance(snt.table, dict)
