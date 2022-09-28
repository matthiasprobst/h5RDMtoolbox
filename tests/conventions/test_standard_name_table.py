import unittest

import yaml

import h5rdmtoolbox
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions import StandardNameTable, StandardNameTableTranslation, StandardName
from h5rdmtoolbox.conventions.standard_attributes.standard_name import merge, MetaDataYamlDict


class TestStandardNameTable(unittest.TestCase):

    def test_metadatayamldict(self):
        test_yamlfilename = generate_temporary_filename(suffix='.yaml')
        with open(test_yamlfilename, 'w') as f:
            yaml.safe_dump({'a': 1}, f)
            f.writelines('---\n')
            yaml.safe_dump({'table': {'b': 2}}, f)
        mdyd = MetaDataYamlDict(test_yamlfilename)
        self.assertDictEqual(mdyd.meta, {'a': 1})
        self.assertFalse(mdyd._data_is_read)
        self.assertDictEqual(mdyd.data, {'b': 2})
        self.assertTrue(mdyd._data_is_read)

    def test_translationtable(self):
        translation = StandardNameTableTranslation('pytest', {'u': 'x_velocity'})
        self.assertIsInstance(translation, StandardNameTableTranslation)
        self.assertDictEqual(translation.translation_dict, {'u': 'x_velocity'})
        snt = StandardNameTable.load_registered('Test-v1')
        translation.register(snt, overwrite=True)
        StandardNameTableTranslation.print_registered()
        del translation
        translation = StandardNameTableTranslation.load_registered('test-to-Test-v1')
        self.assertIsInstance(translation, StandardNameTableTranslation)
        self.assertIsInstance(translation.translation_dict, MetaDataYamlDict)
        self.assertDictEqual(translation.translation_dict.meta, {'snt': 'Test-v1'})
        self.assertDictEqual(translation.translation_dict.data, {'u': 'x_velocity'})

    def test_StandardNameTableFromYaml(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version_number, 1)
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'matthias.probst@kit.edu')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertIsInstance(table._table, dict)

    def test_StandardNameTableFromYaml_special(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable_with_split.yml')
        self.assertEqual(table.name, 'test')
        self.assertEqual(table.version_number, 1)
        self.assertEqual(table.institution, 'ITS')
        self.assertEqual(table.contact, 'matthias.probst@kit.edu')
        self.assertEqual(table.valid_characters, '')
        self.assertEqual(table.pattern, '')
        self.assertIsInstance(table._table, MetaDataYamlDict)
        self.assertDictEqual(table._table._data, {})
        self.assertDictEqual(table.table, {'synthetic_particle_image': {'canonical_units': 'counts',
                                                                        'description': 'Synthetic particle image velocimetry image containing image particles of a single synthetic recording.'},
                                           'mean_particle_diameter': {'canonical_units': 'pixel',
                                                                      'description': 'The mean particle diameter of an image particle. The diameter is defined as the 2 sigma with of the gaussian intensity profile of the particle image.'}})
        self.assertDictEqual(table.alias, {'particle_image': 'synthetic_particle_image'})
        self.assertTrue(table.check_name('synthetic_particle_image'))
        self.assertTrue(table.check_name('particle_image', strict=True))
        self.assertIsInstance(table['particle_image'], StandardName)

    def test_StandardNameTableFromWeb(self):
        cf = StandardNameTable.from_web(
            url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml',
            name='standard_name_table')
        self.assertEqual(cf.name, 'standard_name_table')
        self.assertEqual(cf.versionname, 'standard_name_table-v79')

        opencefa = StandardNameTable.from_gitlab(url='https://git.scc.kit.edu',
                                                 file_path='open_centrifugal_fan_database-v1.yaml',
                                                 project_id='35443',
                                                 ref_name='main')
        self.assertEqual(opencefa.name, 'open_centrifugal_fan_database')
        self.assertEqual(opencefa.versionname, 'open_centrifugal_fan_database-v1')

    def test_from_yaml(self):
        table = StandardNameTable.from_yaml(testdir / 'sntable.yml')

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

    def test_tranlsate_group(self):
        with h5rdmtoolbox.H5File() as h5:
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
