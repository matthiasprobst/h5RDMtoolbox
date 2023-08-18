import pathlib

import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.standard_names import constructor
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
