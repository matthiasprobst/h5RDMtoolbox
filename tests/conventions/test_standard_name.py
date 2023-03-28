"""Testing common funcitonality across all wrapper classs"""

import json
import pathlib
import requests
import unittest
import warnings
from omegaconf import DictConfig
from typing import Union, Dict

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions.cflike import software
from h5rdmtoolbox.conventions.cflike.standard_name import (StandardNameTable,
                                                           StandardNameTableTranslation,
                                                           StandardName,
                                                           url_exists)
from h5rdmtoolbox.conventions.cflike.standard_name import merge
from h5rdmtoolbox.conventions.registration import register_hdf_attr, UserAttr
from h5rdmtoolbox.wrapper.cflike import File
from h5rdmtoolbox.wrapper.cflike import Group


class TestStandardName(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""

        @register_hdf_attr(Group, name='software', overwrite=True)
        class SoftwareAttribute(UserAttr):
            """property attach to a Group"""

            def set(self, sftw: Union[software.Software, Dict]):
                """Get `software` as group attbute"""
                if isinstance(sftw, (tuple, list)):
                    raise TypeError('Software infomration must be provided as dictionary '
                                    f'or object of class Softare, not {type(sftw)}')
                if isinstance(sftw, dict):
                    # init the Software to check for errors
                    self.attrs.create('software', json.dumps(software.Software(**sftw).to_dict()))
                else:
                    self.attrs.create('software', json.dumps(sftw.to_dict()))

            def get(self) -> software.Software:
                """Get `software` from group attbute. The value is expected
                to be a dictionary-string that can be decoded by json.
                However, if it is a real string it is expected that it contains
                name, version url and description separated by a comma.
                """
                raw = self.attrs.get('software', None)
                if raw is None:
                    return software.Software(None, None, None, None)
                if isinstance(raw, dict):
                    return software.Software(**raw)
                try:
                    datadict = json.loads(raw)
                except json.JSONDecodeError:
                    # try figuring out from a string. assuming order and sep=','
                    keys = ('name', 'version', 'url', 'description')
                    datadict = {}
                    raw_split = raw.split(',')
                    n_split = len(raw_split)
                    for i in range(4):
                        if i >= n_split:
                            datadict[keys[i]] = None
                        else:
                            datadict[keys[i]] = raw_split[i].strip()

                return software.Software.from_dict(datadict)

            def delete(self):
                """Delete attribute"""
                self.attrs.__delitem__('standard_name')

    def test_standard_name(self):
        sn1 = StandardName(name='acc',
                           description=None,
                           canonical_units='m**2/s',
                           snt=None)
        self.assertEqual(sn1.canonical_units, 'm**2/s')

        sn2 = StandardName(name='acc',
                           description=None,
                           canonical_units='m^2/s',
                           snt=None)
        self.assertEqual(sn2.canonical_units, 'm**2/s')

        sn3 = StandardName(name='acc',
                           description=None,
                           canonical_units='m/s',
                           snt=None)
        self.assertEqual(sn3.canonical_units, 'm/s')

        self.assertTrue(sn1 == sn2)
        self.assertFalse(sn1 == sn3)
        self.assertTrue(sn1 == 'acc')
        self.assertFalse(sn1 == 'acc2')

        with self.assertRaises(AttributeError):
            self.assertTrue(sn1.check())
        _ = StandardName(name='a',
                         description=None,
                         canonical_units='m^2/s',
                         snt=None)

        sn5 = StandardName(name='a',
                           description=None,
                           canonical_units='m-2/s',
                           snt=None)
        self.assertEqual(sn5.canonical_units, '1/m**2/s')

        self.assertTrue(sn1 != sn3)


class TestStandardNameTable(unittest.TestCase):

    def test_translation_table(self):
        translation = StandardNameTableTranslation('pytest', {'u': 'x_velocity'})
        self.assertIsInstance(translation, StandardNameTableTranslation)
        self.assertDictEqual(translation.translation_dict, {'u': 'x_velocity'})
        snt = StandardNameTable.load_registered('Test-v1')
        translation.register(snt, overwrite=True)
        StandardNameTableTranslation.print_registered()
        del translation
        translation = StandardNameTableTranslation.load_registered('test-to-Test-v1')
        self.assertIsInstance(translation, StandardNameTableTranslation)
        self.assertIsInstance(translation.translation_dict, DictConfig)

    def test_StandardNameTableFromYaml(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version_number, 1)
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'matthias.probst@kit.edu')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertIsInstance(table._table, DictConfig)
        self.assertIsInstance(table.get_table(), str)
        table.rename('mean_particle_diameter', 'mean_particle_diameter2')
        self.assertFalse('mean_particle_diameter' in table)
        self.assertTrue('mean_particle_diameter2' in table)

    def test_StandardNameTableFromYaml_special(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable_with_split.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version_number, 1)
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'matthias.probst@kit.edu')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertIsInstance(table._table, DictConfig)
        self.assertDictEqual(
            table.table,
            {
                'synthetic_particle_image': {
                    'canonical_units': 'counts',
                    'description':
                        'Synthetic particle image velocimetry image containing image particles '
                        'of a single synthetic recording.'
                },
                'mean_particle_diameter': {
                    'canonical_units': 'pixel',
                    'description':
                        'The mean particle diameter of an image particle. The diameter is defined '
                        'as the 2 sigma with of the gaussian intensity profile of the particle image.'
                }
            })
        self.assertDictEqual(table.alias, {'particle_image': 'synthetic_particle_image'}
                             )
        self.assertTrue(table.check_name('synthetic_particle_image'))
        self.assertTrue(table.check_name('particle_image', strict=True))
        self.assertIsInstance(table['particle_image'], StandardName)

    def test_StandardNameTableFromWeb(self):
        cf = StandardNameTable.from_web(
            url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml',
            name='standard_name_table')
        self.assertEqual(cf.name, 'standard_name_table')
        self.assertEqual(cf.versionname, 'standard_name_table-v79')
        self.assertTrue(url_exists(cf.url))
        self.assertFalse(url_exists(cf.url + '123'))

        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            connected = False
            warnings.warn('Cannot check Standard name table from '
                          f'gitlab: {e}')
        if connected:
            opencefa = StandardNameTable.from_gitlab(url='https://git.scc.kit.edu',
                                                     file_path='open_centrifugal_fan_database-v1.yaml',
                                                     project_id='35443',
                                                     ref_name='main')
            self.assertEqual(opencefa.name, 'open_centrifugal_fan_database')
            self.assertEqual(opencefa.versionname, 'open_centrifugal_fan_database-v1')

    def test_from_yaml(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable.yml')
        self.assertIsInstance(table.filename, pathlib.Path)
        self.assertIsInstance(table['synthetic_particle_image'], StandardName)

        with self.assertRaises(ValueError):
            table.modify('not_in_table',
                         description=None,
                         canonical_units=None)

        table.modify('synthetic_particle_image',
                     description='changed the description',
                     canonical_units='m')

        self.assertTrue(table.has_valid_structure())
        table2 = table.copy()
        self.assertTrue(table == table2)
        self.assertFalse(table is table2)
        self.assertTrue(table.compare_versionname(table2))

        snttrans = StandardNameTableTranslation('test', {'images': 'invalid_synthetic_particle_image'})
        with self.assertRaises(KeyError):
            snttrans.verify(table)

        snttrans = StandardNameTableTranslation('test', {'images': 'synthetic_particle_image'})
        self.assertTrue(snttrans.verify(table))

        self.assertEqual(snttrans.translate('images'), 'synthetic_particle_image')

        yaml_filename = table.to_yaml(generate_temporary_filename(suffix='.yml'))
        table2 = StandardNameTable.from_yaml(yaml_filename)
        self.assertEqual(table, table2)
        table2.set('other', 'desc', 'm')
        self.assertNotEqual(table, table2)

    def test_translate_group(self):
        with File() as h5:
            ds1 = h5.create_dataset('ds1', shape=(2,), units='', long_name='a long name')
            ds2 = h5.create_dataset('/grp/ds2', shape=(2,), units='', long_name='a long name')
            translation = {'ds1': 'dataset_one', 'ds2': 'dataset_two'}
            sntt = StandardNameTableTranslation('test', translation)
            sntt.translate_group(h5)
            h5.sdump()

    def test_merge(self):
        registered_snts = StandardNameTable.get_registered()
        new_snt = merge(registered_snts, name='newtable', institution=None,
                        version_number=1, contact='matthias.probst@kit.edu')
        self.assertTrue(new_snt.name, 'newtable')

    def test_empty_SNT(self):
        snt = StandardNameTable('test_snt',
                                table=None,
                                version_number=1,
                                institution='my_institution',
                                contact='mycontact@gmail.com')
        self.assertIsInstance(snt.table, dict)
        self.assertEqual(snt.filename, None)

    def test_wrong_contact(self):
        with self.assertRaises(ValueError):
            StandardNameTable('test_snt',
                              table=None,
                              version_number=1,
                              institution='my_institution',
                              contact='mycontact')
