import unittest
import warnings

import requests

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.errors import StandardNameError
from h5rdmtoolbox.conventions.standard_names import parse_snt
from h5rdmtoolbox.conventions.standard_names.name import StandardName
from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

        self.snt = h5tbx.tutorial.get_standard_name_table()

    def test_standard_name(self):
        with self.assertRaises(ValueError):
            sn = StandardName(name='x_velocty')
        with self.assertWarns(DeprecationWarning):
            sn = StandardName(name='x_velocty', description='Velocity in x-direction', canonical_units='m/s')
        with self.assertRaises(TypeError):
            sn = StandardName(name='x_velocty', description='Velocity in x-direction', units=5.4)

        sn = StandardName(name='x_velocity', description='Velocity in x-direction', units='m/s')
        sn2 = StandardName(name='x_velocity', description='Velocity in x-direction', units='m/s')
        self.assertEqual(sn, 'x_velocity')
        self.assertEqual(sn, sn2)
        sn2.description = 'Velocity in x-direction (m/s)'
        self.assertNotEqual(sn, sn2)

        with self.assertRaises(TypeError):
            StandardName.check_syntax(sn)
        with self.assertRaises(StandardNameError):
            StandardName.check_syntax('123')
        self.assertDictEqual({'name': 'x_velocity', 'units': 'm/s', 'description': 'Velocity in x-direction.'},
                             sn.to_dict())
        self.assertFalse(sn.is_vector())
        snt = parse_snt(h5tbx.tutorial.get_standard_name_table_yaml_file())
        self.assertTrue(sn.check(snt))

    def test_parse_snt(self):
        with self.assertRaises(TypeError):
            parse_snt(None)
        with self.assertRaises(TypeError):
            parse_snt(3.4)
        snt = parse_snt(self.snt)
        self.assertIsInstance(snt, StandardNameTable)
        snt = parse_snt(self.snt.to_dict())
        self.assertIsInstance(snt, StandardNameTable)
        snt = parse_snt(h5tbx.tutorial.get_standard_name_table_yaml_file())
        self.assertIsInstance(snt, StandardNameTable)
        snt = parse_snt(str(h5tbx.tutorial.get_standard_name_table_yaml_file()))
        self.assertIsInstance(snt, StandardNameTable)

    def test_snt_cache(self):
        """caching of SNTs only works if they are zenodo references"""
        cv = h5tbx.conventions.Convention(name='test', contact='me', institution='mine', decoders=())
        from h5rdmtoolbox.conventions.toolbox_validators import standard_name_table as snt_validator
        from pydantic import BaseModel
        class standard_name_table_validator(BaseModel):
            """The standard name table of the convention."""
            value: snt_validator

        sa = h5tbx.conventions.standard_attributes.StandardAttribute(
            name='snt',
            validator=standard_name_table_validator,
            target_method='__init__',
            description='Standard name table.',
            default_value='10.5281/zenodo.8220739'
        )
        cv.add(sa)
        cv.register()

        with h5tbx.use(cv):
            with h5tbx.File() as h5:
                self.assertIsInstance(h5.snt, StandardNameTable)

    def test_StandardNmeTableRaw(self):
        with self.assertRaises(ValueError):  # invalid version:
            snt = StandardNameTable('test', version='1.0', meta={}, standard_names=None)
        snt = StandardNameTable('test', version='v1.0', meta={}, standard_names=None)
        self.assertEqual({}, snt.standard_names)

        with self.assertWarns(UserWarning):
            StandardNameTable('test', version='v1.0', meta={},
                              standard_names={'x_velocity': {
                                  'units': 'm/s', 'alias': 'u'},
                                  'y_velocity': {'canonical_units': 'm/s', 'description': 'y velocity', 'alias': 'v'}
                              })

        snt = StandardNameTable('test', version='v1.0', meta={},
                                standard_names={'x_velocity': {
                                    'units': 'm/s', 'description': 'x velocity.', 'alias': 'u'},
                                    'y_velocity': {'canonical_units': 'm/s', 'description': 'y velocity', 'alias': 'v'}
                                })
        self.assertEqual('x velocity.', snt['x_velocity'].description)
        self.assertEqual('y velocity.', snt['y_velocity'].description)

        self.assertEqual({'u': 'x_velocity', 'v': 'y_velocity'}, snt.aliases)
        self.assertEqual('1.0', snt.version_number)
        snt.meta['version_number'] = '2.0'
        self.assertEqual('2.0', snt.version_number)
        snt.meta.pop('version_number')
        snt.meta.pop('version')
        self.assertEqual(None, snt.version_number)

        self.assertIn('x_velocity', snt)
        self.assertEqual(snt['x_velocity'].description, snt['u'].description)
        self.assertEqual(snt['y_velocity'].description, snt['v'].description)
        with self.assertRaises(StandardNameError):
            print(snt['velocity'])

        with self.assertRaises(TypeError):
            StandardNameTable('test', version='v1.0', meta={},
                              standard_names={},
                              affixes=5.4)

        with self.assertRaises(TypeError):
            StandardNameTable('test', version='v1.0', meta={},
                              standard_names={},
                              affixes={'component': 5.4})

        # with self.assertRaises(ValueError):

    def test_check(self):
        with h5tbx.File() as h5:
            h5.create_dataset('u', data=1, attrs={'standard_name': 'x_velocity', 'units': 'm/s'})
            self.assertEqual(0, len(self.snt.check_hdf_group(h5)))
        self.assertEqual(0, len(self.snt.check_hdf_file(h5.hdf_filename)))
        with h5tbx.File() as h5:
            h5.create_dataset('u', data=1, attrs={'standard_name': 'x_velocity', 'units': 'Pa'})
            self.assertEqual(1, len(self.snt.check_hdf_group(h5)))
        self.assertEqual(1, len(self.snt.check_hdf_file(h5.hdf_filename)))

    def test_StandardNameTableFromYaml(self):
        tmp_filename = h5tbx.utils.generate_temporary_filename('.yaml')
        with open(tmp_filename, 'w') as f:
            f.write(f'<html><h1>503 Service Unavailable</h1></html>')
        self.assertTrue(tmp_filename.exists())
        with self.assertRaises(ConnectionError):
            StandardNameTable.from_yaml(tmp_filename)
        self.assertFalse(tmp_filename.exists())
        table = StandardNameTable.from_yaml(tutorial.get_standard_name_table_yaml_file())
        self.assertIsInstance(table.affixes, dict)
        with self.assertRaises(StandardNameError):
            table['x_time']
        with self.assertRaises(StandardNameError):
            table['x_x_velocity']

        self.assertEqual(table.name, 'Test')
        self.assertEqual(table.version, 'v1.1')
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
        with self.assertRaises(KeyError):
            table.update(a_velocity={
                'description': 'velocity in a direction',
            })
        with self.assertRaises(KeyError):
            table.update(a_velocity={
                'units': 'm/s'
            })
        table.update(a_velocity={
            'description': 'velocity in a direction',
            'units': 'm/s'
        })
        self.assertEqual(table['a_velocity'].description, 'velocity in a direction.')
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

        self.assertEqual(["x_velocity"], snt.names)
        snt_yaml_filename = snt.to_yaml(h5tbx.utils.generate_temporary_filename())
        self.assertTrue(snt_yaml_filename.exists())
        snt_from_yaml = StandardNameTable.from_yaml(snt_yaml_filename)
        self.assertEqual(snt_from_yaml.name, snt.name)
        self.assertEqual(snt_from_yaml.version, snt.version)
        self.assertEqual(list(snt_from_yaml.affixes.keys()), list(snt.affixes.keys()))
        self.assertEqual(snt_from_yaml.standard_names, snt.standard_names)
