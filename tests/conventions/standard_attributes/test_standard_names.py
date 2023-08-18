import inspect
import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.errors import StandardNameError, StandardAttributeError
from h5rdmtoolbox.conventions.standard_attributes import StandardAttribute
from h5rdmtoolbox.conventions.standard_names import constructor
from h5rdmtoolbox.conventions.standard_names import utils
from h5rdmtoolbox.conventions.standard_names.name import StandardName
from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable
from h5rdmtoolbox.conventions.utils import check_url

try:
    import pooch

    pooch_is_available = True
except ImportError:
    pooch_is_available = False
    warnings.warn(f'Cannot test certain things about standard name table because "pooch" is not installed.')


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
        table = StandardNameTable.from_yaml(tutorial.get_reduced_standard_name_table_yaml_file())
        self.assertIsInstance(table['coordinate'], StandardName)
        self.assertIsInstance(table['x_coordinate'], StandardName)
        self.assertEqual('Spatial coordinate. Coordinate is a vector quantity. '
                         'X indicates the x-axis component of the vector.',
                         table['x_coordinate'].description)
        self.assertIsInstance(table['velocity'], StandardName)
        self.assertIsInstance(table['x_velocity'], StandardName)
        with self.assertRaises(h5tbx.errors.StandardNameError):
            table['phi_velocity']
        self.assertIsInstance(table['pressure'], StandardName)
        self.assertFalse(table['pressure'].is_vector())
        self.assertFalse(table['x_velocity'].is_vector())
        self.assertTrue(table['velocity'].is_vector())
        with self.assertRaises(h5tbx.errors.StandardNameError):
            table['x_pressure']
        self.assertIsInstance(table['derivative_of_x_coordinate_wrt_x_velocity'], StandardName)

    # if pooch_is_available:
    def test_StandardNameTableFromYaml(self):
        table = StandardNameTable.from_yaml(tutorial.get_standard_name_table_yaml_file())

        self.assertEqual(table.name, 'Test')
        self.assertEqual(table.version, 'v1.0')
        self.assertEqual(table.institution, 'my_institution')
        self.assertEqual(table.contact, 'https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(table.valid_characters, '[^a-zA-Z0-9_]')
        self.assertEqual(table.pattern, '^[0-9 ].*')

        self.assertIsInstance(table.devices, constructor.StandardConstructors)
        for device in table.devices:
            self.assertIsInstance(device, constructor.StandardConstructor)
        self.assertIsInstance(table.devices['fan'], constructor.StandardConstructor)
        self.assertEqual(table.devices['fan'].name, 'fan')
        self.assertEqual(table.devices['orifice'].name, 'orifice')
        self.assertEqual(table.devices['fan'].description, 'The test fan')
        self.assertEqual(table.devices['orifice'].description, 'The orifice to measure the volume flow rate')
        self.assertEqual(table.devices.names, ['fan', 'orifice'])

        self.assertIsInstance(table.components, constructor.StandardConstructors)
        for component in table.components:
            self.assertIsInstance(component, constructor.StandardConstructor)
        self.assertIsInstance(table.components['x'], constructor.StandardConstructor)
        self.assertEqual(table.components['x'].name, 'x')
        self.assertEqual(table.components['y'].name, 'y')
        self.assertEqual(table.components['z'].name, 'z')
        self.assertEqual(table.components['x'].description, 'X indicates the x-axis component of the vector.')
        self.assertEqual(table.components['y'].description, 'Y indicates the y-axis component of the vector.')
        self.assertEqual(table.components['z'].description, 'Z indicates the z-axis component of the vector.')
        self.assertEqual(table.components.names, ['x', 'y', 'z'])

        self.assertIsInstance(table.locations, constructor.StandardConstructors)
        for location in table.locations:
            self.assertIsInstance(location, constructor.StandardConstructor)
        self.assertIsInstance(table.locations['fan_inlet'], constructor.StandardConstructor)
        self.assertIsInstance(table.locations['fan_outlet'], constructor.StandardConstructor)
        self.assertEqual(table.locations['fan_inlet'].name, 'fan_inlet')
        self.assertEqual(table.locations['fan_outlet'].name, 'fan_outlet')
        ref_desc = 'The defined inlet into the test fan.' \
                   ' See additional meta data or references or the exact spatial location.'
        self.assertEqual(ref_desc, table.locations['fan_inlet'].description)
        ref_desc = 'The defined outlet of the test fan.' \
                   ' See additional meta data or references or the exact spatial location.'
        self.assertEqual(ref_desc, table.locations['fan_outlet'].description)
        self.assertEqual(table.locations.names, ['fan_inlet', 'fan_outlet'])

        with self.assertRaises(AttributeError):
            table.standard_names = {'synthetic_particle_image': {
                'units': 'pixel',
            },
                'mean_particle_diameter2': {
                    'description': 'The mean particle diameter of an image particle. The diameter is defined as the 2 sigma with of the gaussian intensity profile of the particle image.',
                    'units': 'pixel'}
            }

        table._standard_names = {'synthetic_particle_image': {
            'units': 'pixel',
        },
            'mean_particle_diameter2': {
                'description': 'The mean particle diameter of an image particle. The diameter is defined as the 2 sigma with of the gaussian intensity profile of the particle image.',
                'units': 'pixel'}
        }

        table._standard_names = {
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
        self.assertEqual(table.version_number, 1)
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
        self.assertIsInstance(table['synthetic_particle_image'], StandardName)

    def test_empty_SNT(self):
        snt = StandardNameTable(name='test_snt',
                                standard_names={},
                                version='v1.0dev',
                                meta=dict(institution='my_institution',
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        self.assertIsInstance(snt.standard_names, dict)

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

            self.assertTrue(snt.standard_reference_frames is None)

    def test_from_zenodo(self):
        if self.connected:
            import zenodo_search as zsearch
            doi = zsearch.utils.parse_doi('8223533')
            snt = StandardNameTable.from_zenodo(doi=8223533)
            self.assertIsInstance(snt, StandardNameTable)
            filename = h5tbx.UserDir['standard_name_tables'] / f'{doi.replace("/", "_")}.yaml'
            self.assertTrue(filename.exists())
            filename.unlink(missing_ok=True)
            snt = StandardNameTable.from_zenodo(doi=8223533)
            self.assertTrue(filename.exists())

    def test_from_yaml(self):
        if self.connected:
            cv = h5tbx.conventions.from_yaml(tutorial.get_standard_attribute_yaml_filename(), register=True)
            cv.register()
            h5tbx.use(cv)
            with h5tbx.File(title='Test title',
                            piv_method='multi_grid',
                            piv_medium='air',
                            seeding_material='dehs',
                            contact='https://orcid.org/0000-0001-8729-0482') as h5:
                h5.dump()

                with self.assertRaises(StandardAttributeError):
                    h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='difference_of_x_velocity')
                h5.create_dataset('x_velocity', data=1.4, units='km/s', standard_name='x_velocity')

                with self.assertRaises(StandardAttributeError):
                    h5.create_dataset('y_velocity', data=1.4, units='V', standard_name='y_velocity')
                h5.create_dataset('y_velocity', data=1.4, units='V', scale='1 m/s/V', standard_name='y_velocity')

    def test_standard_name_convention(self):
        h5tbx.use(None)
        units_attr = StandardAttribute('units',
                                       validator='$pintunit',
                                       target_methods='create_dataset',
                                       description='A unit of a dataset',
                                       )
        standard_name = StandardAttribute('standard_name',
                                          validator='$standard_name',
                                          target_methods='create_dataset',
                                          description='A standard name of a dataset',
                                          )
        snt_yaml_filename = h5tbx.tutorial.get_standard_attribute_yaml_filename()
        snt = StandardAttribute('standard_name_table',
                                validator='$standard_name_table',
                                target_methods='__init__',
                                # default_value='https://zenodo.org/record/8158764',
                                default_value=snt_yaml_filename,
                                description='A standard name table',
                                requirements=['standard_name', 'units'],
                                return_type='standard_name_table'
                                )

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

                with self.assertRaises(AttributeError):
                    snt.devices = ['fan', 'orifice']

    def test_X_at_LOC(self):
        # X_at_LOC
        for sn in self.snt.standard_names:
            with self.assertRaises(KeyError):
                self.snt[f'{sn}_at_fan']
        with self.assertRaises(h5tbx.errors.StandardNameError):
            self.snt['invalid_coordinate_at_fan']
        sn = self.snt['x_coordinate_at_fan_inlet']
        self.assertEqual(sn.units, self.snt['x_coordinate'].units)

    def test_difference_of_X_and_Y_between_LOC1_and_LOC2(self):
        # difference_of_X_and_Y_between_LOC1_and_LOC2
        self.snt['difference_of_x_coordinate_and_y_coordinate_between_fan_outlet_and_fan_inlet']
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                for loc1 in self.snt.locations:
                    for loc2 in self.snt.locations:
                        if self.snt[sn1].units != self.snt[sn2].units:
                            with self.assertRaises(ValueError):
                                self.snt[f'difference_of_{sn1}_and_{sn2}_between_{loc1}_and_{loc2}']
                        else:
                            _sn = self.snt[f'difference_of_{sn1}_and_{sn2}_between_{loc1}_and_{loc2}']
                            self.assertEqual(_sn.units, self.snt[sn1].units)
                            self.assertEqual(_sn.units, self.snt[sn2].units)
                            self.assertEqual(_sn.description, f"Difference of {sn1} and {sn2} between {loc1} and "
                                                              f"{loc2}")
        with self.assertRaises(KeyError):
            self.snt[f'difference_of_time_and_time_between_fan_inlet_and_INVALID']
        with self.assertRaises(KeyError):
            self.snt[f'difference_of_time_and_time_between_INVALID_and_fan_outlet']

    def test_difference_of_X_and_Y_across_device(self):
        # difference_of_X_and_Y_across_device
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                for dev in self.snt.devices:
                    if self.snt[sn1].units != self.snt[sn2].units:
                        with self.assertRaises(ValueError):
                            self.snt[f'difference_of_{sn1}_and_{sn2}_across_{dev}']
                    else:
                        _sn = self.snt[f'difference_of_{sn1}_and_{sn2}_across_{dev}']
                        self.assertEqual(_sn.units, self.snt[sn1].units)
                        self.assertEqual(_sn.units, self.snt[sn2].units)
                        self.assertEqual(_sn.description, f"Difference of {sn1} and {sn2} across {dev}")
        with self.assertRaises(KeyError):
            self.snt[f'difference_of_time_and_time_across_INVALID']

    def test_ratio_of_X_and_Y(self):
        # ratio_of_X_and_Y
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                _sn = self.snt[f'ratio_of_{sn1}_and_{sn2}']
                self.assertEqual(_sn.units, self.snt[sn1].units / self.snt[sn2].units)
                self.assertEqual(_sn.description, f"Ratio of {sn1} and {sn2}")

    def test_difference_of_X_across_device(self):
        # difference_of_X_across_device
        for sn in self.snt.standard_names:
            for dev in self.snt.devices:
                _sn = self.snt[f'difference_of_{sn}_across_{dev}']
                self.assertEqual(_sn.units, self.snt[sn].units)
                self.assertEqual(_sn.description, f"Difference of {sn} across {dev}")
        with self.assertRaises(KeyError):
            self.snt[f'difference_of_{sn}_across_INVALID']

    def test_square_of_X(self):
        # square_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'square_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units * self.snt[sn].units)
            self.assertEqual(_sn.description, f"Square of {sn}")

    def test_standard_deviation_of(self):
        # standard_deviation_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'standard_deviation_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Standard deviation of {sn}")

    def test_arithmetic_mean_of(self):
        # arithmetic_mean_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'arithmetic_mean_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Arithmetic mean of {sn}")

    def test_magnitude_of(self):
        # magnitude_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'magnitude_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Magnitude of {sn}")

    def test_product_of_X_and_Y(self):
        # product_of_X_and_Y
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                _sn = self.snt[f'product_of_{sn1}_and_{sn2}']
                self.assertEqual(_sn.units, self.snt[sn1].units * self.snt[sn2].units)
                self.assertEqual(_sn.description, f"Product of {sn1} and {sn2}")

    def test_in_frame(self):
        for sn in self.snt.standard_names:
            for frame in self.snt.standard_reference_frames.names:
                _sn = self.snt[f'{sn}_in_{frame}']
                self.assertEqual(_sn.units, self.snt[sn].units)
        with self.assertRaises(StandardNameError):
            self.snt[f'{sn}_in_invalid_frame']
        with self.assertRaises(StandardNameError):
            self.snt.check(f'{sn}_in_invalid_frame')
