import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.convention.errors import StandardNameError, StandardAttributeError
from h5rdmtoolbox.convention.standard_names import utils
from h5rdmtoolbox.convention.standard_names.name import StandardName
from h5rdmtoolbox.convention.standard_names.table import StandardNameTable
from h5rdmtoolbox.convention.utils import check_url


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

    def test_StandardNameTableFromWeb(self):
        try:
            import xmltodict
            xmltodict_exists = True
        except ImportError:
            xmltodict_exists = False
            warnings.warn('xmltodict not installed. Cannot test "test_StandardNameTableFromWeb"', UserWarning)
        if xmltodict_exists:
            cf = StandardNameTable.from_web(
                url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml',
                name='standard_name_table',
                known_hash='4c29b5ad70f6416ad2c35981ca0f9cdebf8aab901de5b7e826a940cf06f9bae4')
            self.assertEqual(cf.name, 'standard_name_table')
            self.assertEqual(cf.versionname, 'standard_name_table-v79.0.0')
            if self.connected:
                self.assertTrue(check_url(cf.meta['url']))
                self.assertFalse(check_url(cf.meta['url'] + '123'))

            if self.connected:
                opencefa = StandardNameTable.from_gitlab(url='https://gitlab.kit.edu',
                                                         file_path='open_centrifugal_fan_database-v1.yaml',
                                                         project_id='166713',
                                                         ref_name='main')
                self.assertEqual(opencefa.name, 'open_centrifugal_fan_database')
                self.assertEqual(opencefa.versionname, 'open_centrifugal_fan_database-v1.0.0')

    def test_StandardNameTableFromYaml_special(self):
        table = StandardNameTable.from_yaml(tutorial.testdir / 'sntable_with_split.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version, 'v1.0.0')
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
        with self.assertRaises(ValueError):
            snt = StandardNameTable(name='test_snt',
                                    standard_names={},
                                    version='v1.0.0beta',
                                    meta=dict(institution='my_institution',
                                              contact='https://orcid.org/0000-0001-8729-0482'))
        snt = StandardNameTable(name='test_snt',
                                standard_names={},
                                version='v1.0.0-beta',
                                meta=dict(institution='my_institution',
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        self.assertEqual('v1.0.0-beta', snt.version)
        self.assertIsInstance(snt.standard_names, dict)

        snt = StandardNameTable(name='test_snt',
                                standard_names={},
                                version=None,
                                affixes={'table': {'x_velocity': {'units': 'm/s', 'description': 'x velocity'}}},
                                meta=dict(institution='my_institution',
                                          version_number=1,
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        self.assertListEqual(['x_velocity', ], snt.names)
        self.assertEqual('v1.0.0', snt.version)

        self.assertIsInstance(snt.to_dict(), dict)
        self.assertIsInstance(snt.to_json(), str)

        with self.assertRaises(TypeError):
            StandardNameTable(name='test_snt',
                              standard_names={},
                              version='v1.0.0-beta',
                              affixes=4.3,
                              meta=dict(institution='my_institution',
                                        contact='https://orcid.org/0000-0001-8729-0482'))

    def test_to_html(self):
        try:
            import pypandoc
            from h5rdmtoolbox.utils import generate_temporary_filename
            fname = generate_temporary_filename(touch=False)
            with open(fname, 'w') as f:
                f.write('# test')
            pypandoc.convert_file(fname, 'html', format='md')
            pypandoc_works = True
        except OSError:
            pypandoc_works = False
            warnings.warn('pypandoc not properly installed. Cannot test "test_to_html"', UserWarning)

        if self.connected and pypandoc_works:
            snt = StandardNameTable(name='test_snt',
                                    standard_names={'x_velocity': {'units': 'm/s', 'description': 'x velocity'}},
                                    version='v1.0.0-beta',
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
            snt = StandardNameTable.from_zenodo(doi_or_recid=10428795)
            self.assertIsInstance(snt, StandardNameTable)
            filename = h5tbx.UserDir['standard_name_tables'] / f'10428795.yaml'
            self.assertTrue(filename.exists())
            # filename.unlink(missing_ok=True)

    def test_from_yaml(self):
        cv = h5tbx.convention.from_yaml(tutorial.get_convention_yaml_filename(), overwrite=True)
        h5tbx.use(cv)

        with h5tbx.File(contact='https://orcid.org/0000-0001-8729-0482', data_type='numerical') as h5:
            with self.assertRaises(StandardAttributeError):
                # velocity not found!
                h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='velocity')
            h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='x_velocity')

            with self.assertRaises(StandardAttributeError):
                # wrong units!
                h5.create_dataset('y_velocity', data=1.4, units='V', standard_name='y_velocity')

            ds_scale = h5.create_dataset('y_velocity_scale', data=2, units='m/s/V')

            ds_yvel = h5.create_dataset('y_velocity', data=1.4,
                                        attach_data_scale=ds_scale,
                                        units='V',
                                        standard_name='y_velocity')
            self.assertEqual(ds_yvel.attrs['standard_name'], 'y_velocity')

            with self.assertRaises(StandardAttributeError):
                h5.create_dataset('velocity', data=2.3, units='m/s', standard_name='velocity')
