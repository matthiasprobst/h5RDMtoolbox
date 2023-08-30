import inspect
import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.errors import StandardNameError, StandardAttributeError, AffixKeyError
from h5rdmtoolbox.conventions.standard_attributes import StandardAttribute
from h5rdmtoolbox.conventions.standard_names import utils
from h5rdmtoolbox.conventions.standard_names.name import StandardName
from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable
from h5rdmtoolbox.conventions.utils import check_url
from h5rdmtoolbox.conventions.validators import ORCIDValidator


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

        self.snt = h5tbx.tutorial.get_standard_name_table()

    def test_orcid(self):
        o = ORCIDValidator()

        with self.assertRaises(TypeError):
            o(3.4)
        self.assertTrue(o(h5tbx.__author_orcid__))
        self.assertTrue(o('0000-0001-8729-0482'))
        self.assertTrue(o(['0000-0001-8729-0482', '0000-0001-8729-0482']))
        with self.assertRaises(ValueError):
            o('0000-0001-8729-048X')
        with self.assertRaises(ValueError):
            o('0000-0001-8729-048Y')

    def test_units_power_fix(self):
        self.assertEqual('m s^-1', utils._units_power_fix('m s-1'))

    def test_update_datasets(self):
        with h5tbx.use(None):
            with h5tbx.File() as h5:
                h5.attrs['test'] = 1
                h5.create_dataset('grp/ds', data=1, attrs={'test': 2, 'long_name': 'x velocity'})
                h5.create_dataset('ds', data=1, attrs={'test': 2, 'long_name': 'x velocity'})
                h5.create_dataset('ds2', data=1, attrs={'test': 2, 'long_name': 'x velocity'})
                utils.update_datasets(group_or_filename=h5,
                                      translation_dict={'ds': 'x_velocity'}, rec=False)
                self.assertFalse('standard_name' in h5['grp/ds'].attrs)
                self.assertTrue('standard_name' in h5['ds'].attrs)
                self.assertFalse('standard_name' in h5['ds2'].attrs)
            utils.update_datasets(group_or_filename=h5.hdf_filename,
                                  translation_dict={'ds': 'x_velocity'}, rec=False)
            with h5tbx.File(h5.hdf_filename) as h5:
                self.assertFalse('standard_name' in h5['grp/ds'].attrs)
                self.assertTrue('standard_name' in h5['ds'].attrs)
                self.assertFalse('standard_name' in h5['ds2'].attrs)
            utils.update_datasets(group_or_filename=h5.hdf_filename,
                                  translation_dict={'ds': 'x_velocity'}, rec=True)
            with h5tbx.File(h5.hdf_filename) as h5:
                self.assertTrue('standard_name' in h5['grp/ds'].attrs)
                self.assertTrue('standard_name' in h5['ds'].attrs)
                self.assertFalse('standard_name' in h5['ds2'].attrs)
                self.assertEqual('x_velocity', h5['grp/ds'].attrs['standard_name'])
                self.assertEqual('x_velocity', h5['ds'].attrs['standard_name'])

    def test_add_transformation(self):
        snt = h5tbx.tutorial.get_standard_name_table()
        with self.assertRaises(TypeError):
            snt.add_transformation(3.2)

    def test_standard_name(self):
        with self.assertRaises(StandardNameError):
            StandardName(name='', units='m')

        with self.assertRaises(StandardNameError):
            StandardName(name=' x', units='m', description='a description')

        with self.assertRaises(StandardNameError):
            StandardName(name='x ', units='m', description='a description')

        sn1 = StandardName(name='acc',
                           description='a description',
                           units='m**2/s')
        self.assertEqual(sn1.units, h5tbx.get_ureg().Unit('m**2/s'))

        with self.assertRaises(StandardNameError):
            tutorial.get_standard_name_table()['z_coord']

    def test_ReducedStandardNameTableFromYaml(self):
        table = StandardNameTable.from_yaml(tutorial.get_standard_name_table_yaml_file())
        self.assertIsInstance(table['coordinate'], StandardName)
        self.assertIsInstance(table['x_coordinate'], StandardName)
        self.assertEqual('Coordinate refers to the spatial coordinate. Coordinate is a vector '
                         'quantity. X indicates the x-axis component of the vector.',
                         table['x_coordinate'].description)
        self.assertIsInstance(table['velocity'], StandardName)
        self.assertIsInstance(table['x_velocity'], StandardName)
        with self.assertRaises(h5tbx.errors.StandardNameError):
            table['phi_velocity']
        self.assertIsInstance(table['static_pressure'], StandardName)
        self.assertFalse(table['static_pressure'].is_vector())
        self.assertFalse(table['x_velocity'].is_vector())
        self.assertTrue(table['velocity'].is_vector())
        with self.assertRaises(h5tbx.errors.StandardNameError):
            table['x_pressure']
        self.assertIsInstance(table['derivative_of_x_coordinate_wrt_x_velocity'], StandardName)

        table['x_velocity_in_stationary_frame']

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
            name='standard_name_table',
            known_hash='4c29b5ad70f6416ad2c35981ca0f9cdebf8aab901de5b7e826a940cf06f9bae4')
        self.assertEqual(cf.name, 'standard_name_table')
        self.assertEqual(cf.versionname, 'standard_name_table-v79')
        if self.connected:
            self.assertTrue(check_url(cf.meta['url']))
            self.assertFalse(check_url(cf.meta['url'] + '123'))

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
        self.assertEqual(table.version_number, str(1))
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertDictEqual(
            table.standard_names,
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
        self.assertTrue(table.check_name('synthetic_particle_image'))
        self.assertFalse(table.check_name('particle_image'))
        self.assertTrue(table.check(table['mean_particle_diameter']))
        self.assertFalse(table.check(StandardName(name='particle_image', units='counts', description='a description')))
        self.assertIsInstance(table['synthetic_particle_image'], StandardName)

    def test_empty_SNT(self):
        snt = StandardNameTable(name='test_snt',
                                standard_names={},
                                version='v1.0dev',
                                meta=dict(institution='my_institution',
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        self.assertIsInstance(snt.standard_names, dict)

        snt = StandardNameTable(name='test_snt',
                                standard_names={},
                                version=None,
                                affixes={'table': {'x_velocity': {'units': 'm/s', 'description': 'x velocity'}}},
                                meta=dict(institution='my_institution',
                                          version_number=1,
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        self.assertListEqual(['x_velocity', ], snt.names)
        self.assertEqual('v1', snt.version)
        self.assertEqual('v0.0', StandardNameTable.validate_version(None))

        with self.assertRaises(TypeError):
            StandardNameTable(name='test_snt',
                              standard_names={},
                              version='v1.0dev',
                              affixes=4.3,
                              meta=dict(institution='my_institution',
                                        contact='https://orcid.org/0000-0001-8729-0482'))

    def test_to_html(self):
        if self.connected:
            snt = StandardNameTable(name='test_snt',
                                    standard_names={'x_velocity': {'units': 'm/s', 'description': 'x velocity'}},
                                    version='v1.0dev',
                                    meta=dict(institution='my_institution',
                                              contact='https://orcid.org/0000-0001-8729-0482')
                                    )
            fname = snt.to_html('test.html')
            self.assertTrue(fname.exists())
            fname.unlink(missing_ok=True)

            with self.assertRaises(StandardNameError):
                self.snt['x_velocity_in_a_frame']

    def test_from_zenodo(self):
        if self.connected:
            import zenodo_search as zsearch
            doi = zsearch.utils.parse_doi('8266929')
            snt = StandardNameTable.from_zenodo(doi=8266929)
            self.assertIsInstance(snt, StandardNameTable)
            filename = h5tbx.UserDir['standard_name_tables'] / f'{doi.replace("/", "_")}.yaml'
            self.assertTrue(filename.exists())
            filename.unlink(missing_ok=True)

    def test_from_yaml(self):
        cv = h5tbx.conventions.from_yaml(tutorial.get_standard_attribute_yaml_filename(), register=True)
        cv.decoders = ('scale_and_offset',)
        cv.add(StandardAttribute(name='scale',
                                 validator='$pintquantity',
                                 target_method='create_dataset',
                                 description='Scale factor for the dataset values.',
                                 position={'after': 'data'},
                                 default_value=StandardAttribute.NONE))
        cv.register()
        h5tbx.use(cv)
        with h5tbx.File(contact='https://orcid.org/0000-0001-8729-0482', data_type='numerical') as h5:
            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='difference_of_x_velocity')
            h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='x_velocity')

            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('y_velocity', data=1.4, units='V', standard_name='y_velocity')
            h5.create_dataset('y_velocity', data=1.4, units='V', scale='1 m/s/V', standard_name='y_velocity')
            self.assertEqual(h5['y_velocity'].attrs['standard_name'], 'y_velocity')

            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('velocity', data=2.3, units='m/s', standard_name='velocity')

    def test_standard_name_convention(self):
        h5tbx.use(None)
        units_attr = StandardAttribute('units',
                                       validator='$pintunit',
                                       target_method='create_dataset',
                                       description='A unit of a dataset',
                                       )
        standard_name = StandardAttribute('standard_name',
                                          validator='$standard_name',
                                          target_method='create_dataset',
                                          description='A standard name of a dataset',
                                          )
        snt_yaml_filename = h5tbx.tutorial.get_standard_attribute_yaml_filename()
        snt = StandardAttribute('standard_name_table',
                                validator='$standard_name_table',
                                target_method='__init__',
                                # default_value='https://zenodo.org/record/8158764',
                                default_value=snt_yaml_filename,
                                description='A standard name table',
                                requirements=['standard_name', 'units'])

        cv = h5tbx.conventions.Convention('test_standard_name',
                                          contact=h5tbx.__author_orcid__)
        cv.add(units_attr)
        cv.add(standard_name)
        cv.add(snt)

        cv.register()
        h5tbx.use(cv.name)

        self.assertIn('standard_name', inspect.signature(h5tbx.Group.create_dataset).parameters.keys())
        self.assertIn('units', inspect.signature(h5tbx.Group.create_dataset).parameters.keys())
        self.assertIn('standard_name_table', inspect.signature(h5tbx.File.__init__).parameters.keys())

        if self.connected:
            with h5tbx.File(standard_name_table='https://zenodo.org/record/8220739') as h5:
                self.assertIsInstance(h5.standard_name_table, StandardNameTable)

                h5.create_dataset('test', data=1, standard_name='x_velocity', units='m/s')

                snt = h5.standard_name_table
