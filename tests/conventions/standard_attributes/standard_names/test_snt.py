import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.errors import StandardNameError, AffixKeyError
from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)
        try:
            import pooch

            self.pooch_is_available = True
        except ImportError:
            self.pooch_is_available = False
            warnings.warn(f'Cannot test certain things about standard name table because "pooch" is not installed.')

        self.snt = h5tbx.tutorial.get_standard_name_table()

    def test_StandardNameTableFromYaml(self):
        table = StandardNameTable.from_yaml(tutorial.get_standard_name_table_yaml_file())
        self.assertIsInstance(table.affixes, dict)
        with self.assertRaises(StandardNameError):
            table['x_time']
        with self.assertRaises(AffixKeyError):
            table['x_x_velocity']
        table['x_velocity']

        self.assertEqual(table.name, 'Test')
        self.assertEqual(table.version, 'v1.0')
        self.assertEqual(table.institution, 'my_institution')
        self.assertEqual(table.contact, 'https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(table.valid_characters, '[^a-zA-Z0-9_]')
        self.assertEqual(table.pattern, '^[0-9 ].*')

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

    def test_to_dict(self):
        snt = StandardNameTable(name='test_snt',
                                standard_names={'x_velocity': {'units': 'm/s', 'description': 'x velocity'}},
                                version='v1.0dev',
                                affixes=dict(component={'description': 'test component',
                                                        'x': {'description': 'x coordinate'},
                                                        'y': {'description': 'y coordinate'},
                                                        'z': {'description': 'z coordinate'}}),
                                meta=dict(institution='my_institution',
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        snt_dict = snt.to_dict()
        self.assertIn('standard_names', snt_dict)
        self.assertIn('affixes', snt_dict)

    def test_to_from_yaml(self):
        snt = StandardNameTable(name='test_snt',
                                standard_names={'x_velocity': {'units': 'm/s', 'description': 'x velocity'}},
                                version='v1.0dev',
                                affixes=dict(component={'description': 'test component',
                                                        'x': {'description': 'x coordinate'},
                                                        'y': {'description': 'y coordinate'},
                                                        'z': {'description': 'z coordinate'}}),
                                meta=dict(institution='my_institution',
                                          contact='https://orcid.org/0000-0001-8729-0482'))
        snt_yaml_filename = snt.to_yaml(h5tbx.utils.generate_temporary_filename())
        self.assertTrue(snt_yaml_filename.exists())
        snt_from_yaml = StandardNameTable.from_yaml(snt_yaml_filename)
        self.assertEqual(snt_from_yaml.name, snt.name)
        self.assertEqual(snt_from_yaml.version, snt.version)
        self.assertEqual(list(snt_from_yaml.affixes.keys()), list(snt.affixes.keys()))
        self.assertEqual(snt_from_yaml.standard_names, snt.standard_names)
