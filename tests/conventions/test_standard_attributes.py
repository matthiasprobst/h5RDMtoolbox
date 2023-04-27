"""Testing the standard attributes"""
import pathlib
import requests
import unittest
import warnings
from omegaconf import DictConfig
from packaging import version
from pint.errors import UndefinedUnitError

import h5rdmtoolbox
import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import conventions
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox import tutorial
from h5rdmtoolbox._config import ureg
from h5rdmtoolbox._user import testdir
from h5rdmtoolbox.conventions import units, title, standard_name
from h5rdmtoolbox.conventions.layout.tbx import IsValidVersionString, IsValidUnit


class TestStandardAttributes(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_registration(self):

        class shortyname(h5tbx.conventions.StandardAttribute):
            """Shorty name attribute"""

            def set(self, value):
                """Only take the first 3 characters"""
                super().set(value[0:3])

            def get(self, src=None, name=None, default=None):
                """Get the short_name and add a '!'"""
                return super().get() + '!'

        class ShortyAttribute(h5tbx.conventions.StandardAttribute):
            """Shorty name attribute"""

            name = 'another_shorty_name'

            def set(self, value):
                """Only take the first 3 characters"""
                super().set(value[0:4])

            def get(self, src=None, name=None, default=None):
                """Get the short_name and add a '!'"""
                return super().get() + '!!'

        cv = conventions.Convention('short_name_convention')
        cv.add(shortyname,
               target_cls=h5tbx.wrapper.core.Group,
               add_to_method=True,
               position={'after': 'name'},
               optional=True)

        # this shall be a required attribute:
        cv.add(ShortyAttribute,
               target_cls=h5tbx.wrapper.core.Group,
               add_to_method=True,
               position={'after': 'name'},
               optional=False)
        cv.add(ShortyAttribute,
               target_cls=h5tbx.wrapper.core.Dataset,
               add_to_method=True,
               position={'after': 'name'},
               optional=False)

        cv.register()
        self.assertIn(cv.name, h5tbx.conventions.registered_conventions)
        h5tbx.use(cv.name)
        self.assertEqual(cv, h5tbx.conventions.current_convention)

        with h5tbx.File() as h5:
            h5.short_name = 'short'
            h5.shortyname = 'not_effect'
            self.assertNotIn('short_name', h5.attrs.keys())
            self.assertNotIn('shortyname', h5.attrs.keys())

            h5['/'].short_name = 'short'
            h5['/'].shortyname = 'shorty'
            h5['/'].another_shorty_name = 'shorty'
            self.assertEqual(h5.attrs['shortyname'], 'sho')
            self.assertEqual(h5['/'].attrs['shortyname'], 'sho!')
            self.assertEqual(h5['/'].attrs['another_shorty_name'], 'shor!!')

            with self.assertRaises(h5tbx.conventions.StandardAttributeError):
                h5.create_dataset('test', data=1)
            h5.create_dataset('test', data=1, another_shorty_name='shorty')
            self.assertEqual(h5['test'].another_shorty_name, 'shor!!')

            self.assertEqual(h5['/'].shortyname, 'sho!')
            self.assertEqual(h5['/'].another_shorty_name, 'shor!!')

            self.assertEqual(h5.shortyname, 'not_effect')
            h5tbx.use(None)
            with self.assertRaises(AttributeError):
                self.assertNotEqual(h5['/'].shortyname, 'sho!')
            self.assertEqual(h5.attrs['shortyname'], 'sho')

    def test_references(self):
        # bibtex dict example taken from https://bibtexparser.readthedocs.io/en/master/tutorial.html#step-2-parse-it
        bibtex_entry = {'journal': 'Nice Journal',
                        'comments': 'A comment',
                        'pages': '12--23',
                        'month': 'jan',
                        'abstract': 'This is an abstract. This line should be long enough to test\nmultilines...',
                        'title': 'An amazing title',
                        'year': '2013',
                        'volume': '12',
                        'ID': 'Cesar2013',
                        'author': 'Jean Cesar',
                        'keyword': 'keyword1, keyword2',
                        'ENTRYTYPE': 'article'}
        url = 'https://h5rdmtoolbox.readthedocs.io/en/latest/'

        cv = conventions.Convention('test_references')
        cv.add(attr_cls=conventions.references.ReferencesAttribute,
               target_cls=h5tbx.wrapper.core.File,
               add_to_method=True,
               position={'before': 'layout'},
               optional=True)
        cv.register()
        h5tbx.use(cv.name)

        with h5tbx.File() as h5:
            h5.references = bibtex_entry
            self.assertDictEqual(h5.references, bibtex_entry)

            h5.references = url
            self.assertEqual(h5.references, url)

            h5.references = (bibtex_entry, url)
            self.assertTupleEqual(h5.references, (url, bibtex_entry))

            h5.references = (url, bibtex_entry)
            self.assertTupleEqual(h5.references, (url, bibtex_entry))

            h5.references = (url, bibtex_entry, url)
            self.assertTupleEqual(h5.references, (url, url, bibtex_entry))

            h5.references = (bibtex_entry, url, bibtex_entry)
            self.assertTupleEqual(h5.references, (url, bibtex_entry, bibtex_entry))

            h5.references = (url, bibtex_entry, url, url)
            self.assertTupleEqual(h5.references, (url, url, url, bibtex_entry))

            h5.references = (url, url, bibtex_entry, url, url)
            self.assertTupleEqual(h5.references, (url, url, url, url, bibtex_entry))

            h5.references = (url, url, bibtex_entry, bibtex_entry, url, url)
            self.assertTupleEqual(h5.references, (url, url, url, url, bibtex_entry, bibtex_entry))

            h5.references = (url, url, url, url, bibtex_entry, bibtex_entry, bibtex_entry)
            self.assertTupleEqual(h5.references, (url, url, url, url, bibtex_entry, bibtex_entry, bibtex_entry))
        h5tbx.use(None)

    # def setUp(self) -> None:
    #     """setup"""
    #
    #     @register_standard_attr(Group, name='software', overwrite=True)
    #     class SoftwareAttribute(StandardAttribute):
    #         """property attach to a Group"""
    #
    #         def set(self, sftw: Union[software.Software, Dict]):
    #             """Get `software` as group attribute"""
    #             if isinstance(sftw, (tuple, list)):
    #                 raise TypeError('Software information must be provided as dictionary '
    #                                 f'or object of class Software, not {type(sftw)}')
    #             if isinstance(sftw, dict):
    #                 # init the Software to check for errors
    #                 self.attrs.create('software', json.dumps(software.Software(**sftw).to_dict()))
    #             else:
    #                 self.attrs.create('software', json.dumps(sftw.to_dict()))
    #
    #         @staticmethod
    #         def parse(raw, obj=None):
    #             if raw is None:
    #                 return software.Software(None, None, None, None)
    #             if isinstance(raw, dict):
    #                 return software.Software(**raw)
    #             try:
    #                 datadict = json.loads(raw)
    #             except json.JSONDecodeError:
    #                 # try figuring out from a string. assuming order and sep=','
    #                 keys = ('name', 'version', 'url', 'description')
    #                 datadict = {}
    #                 raw_split = raw.split(',')
    #                 n_split = len(raw_split)
    #                 for i in range(4):
    #                     if i >= n_split:
    #                         datadict[keys[i]] = None
    #                     else:
    #                         datadict[keys[i]] = raw_split[i].strip()
    #
    #             return software.Software.from_dict(datadict)
    #
    #         def get(self) -> software.Software:
    #             """Get `software` from group attribute. The value is expected
    #             to be a dictionary-string that can be decoded by json.
    #             However, if it is a real string it is expected that it contains
    #             name, version url and description separated by a comma.
    #             """
    #             return SoftwareAttribute.parse(self.attrs.get('software', None))
    #
    #         def delete(self):
    #             """Delete attribute"""
    #             self.attrs.__delitem__('standard_name')

    # def test_software(self):
    #     meta = metadata('numpy')
    #
    #     s = software.Software(meta['Name'], version=meta['Version'], url=meta['Home-page'],
    #                           description=meta['Summary'])
    #
    #     with h5tbx.File() as h5:
    #         h5.software = s
    #
    # def test_long_name(self):
    #     # is available per default
    #     with h5tbx.File() as h5:
    #         with self.assertRaises(LongNameError):
    #             h5.attrs['long_name'] = ' 1234'
    #         with self.assertRaises(LongNameError):
    #             h5.attrs['long_name'] = '1234'
    #         h5.attrs['long_name'] = 'a1234'
    #         with self.assertRaises(LongNameError):
    #             h5.create_dataset('ds1', shape=(2,), long_name=' a long name', units='m**2')
    #         with self.assertRaises(LongNameError):
    #             h5.create_dataset('ds3', shape=(2,), long_name='123a long name ', units='m**2')
    #
    # def test_units(self):
    #     # is available per default
    #     import pint
    #     with h5tbx.File() as h5:
    #         h5.attrs['units'] = ' '
    #         h5.attrs['units'] = 'hallo'
    #
    #         h5.create_dataset('ds1', shape=(2,), long_name='a long name', units='m**2')
    #
    #         with self.assertRaises(pint.errors.UndefinedUnitError):
    #             h5['ds1'].units = 'no unit'
    #
    #         with self.assertRaises(pint.errors.UndefinedUnitError):
    #             h5.create_dataset('ds2', shape=(2,), long_name='a long name', units='nounit')
    #
    # def test_user(self):
    #     use(None)
    #     with CoreFile() as h5:
    #         self.assertEqual(h5.user, None)
    #         h5.attrs['responsible_person'] = '1123-0814-1234-2343'
    #         self.assertEqual(h5.user, '1123-0814-1234-2343')
    #
    #     with CoreFile() as h5:
    #         with self.assertRaises(OrcidError):
    #             h5.user = '11308429'
    #         with self.assertRaises(OrcidError):
    #             h5.attrs['responsible_person'] = '11308429'
    #         with self.assertRaises(OrcidError):
    #             h5.user = '123-132-123-123'
    #         with self.assertRaises(OrcidError):
    #             h5.user = '1234-1324-1234-1234s'
    #         h5.user = '1234-1324-1234-1234'
    #         self.assertTrue(h5.user, '1234-1324-1234-1234')
    #         h5.user = ['1234-1324-1234-1234', ]
    #         self.assertTrue(h5.user, ['1234-1324-1234-1234', ])
    #
    #         g = h5.create_group('g1')
    #         from h5rdmtoolbox import config
    #         config.natural_naming = False
    #         with self.assertRaises(RuntimeError):
    #             g.attrs.user = '123'
    #         config.natural_naming = True
    #     use('tbx')
    #
    # def test_set_attribute_to_higher_class(self):
    #     @register_standard_attr(CoreFile, name=None, overwrite=True)
    #     class shortyname2(StandardAttribute):
    #         """Shorty name attribute"""
    #         pass
    #
    #     with CoreFile() as h5:
    #         # shortyname2 only available for classes inherited from File
    #         h5.shortyname2 = 'my short name2'
    #         self.assertIn('shortyname2', h5.attrs.keys())
    #     with h5tbx.File() as h5:
    #         h5.shortyname2 = 'my short name2'
    #         self.assertNotIn('shortyname', h5.attrs.keys())

    def test_comment(self):
        h5rdmtoolbox.use('tbx')
        with h5rdmtoolbox.File() as h5:
            self.assertEqual(h5.comment, None)
            with self.assertRaises(conventions.comment.CommentError):
                h5.comment = ' This is a comment, which starts with a space.'
            with self.assertRaises(conventions.comment.CommentError):
                h5.comment = '9 This is a comment, which starts with a number.'
            with self.assertRaises(conventions.comment.CommentError):
                h5.comment = 'Too short'
            with self.assertRaises(conventions.comment.CommentError):
                h5.comment = 'Too long' * 100

            h5.comment = 'This comment is ok.'
            self.assertEqual(h5.comment, 'This comment is ok.')

    def test_units(self):
        """Test title attribute"""
        h5rdmtoolbox.use('tbx')
        with h5rdmtoolbox.File() as h5:
            ds = h5.create_dataset('test', data=[1, 2, 3], units='m', long_name='test')
            with self.assertRaises(UndefinedUnitError):
                ds.units = 'test'
            with self.assertRaises(units.UnitsError):
                ds.units = ('test',)
            self.assertEqual(ds.units, 'm')
            # creat pint unit object:
            ds.units = ureg.mm
            self.assertEqual(ds.units, 'mm')
            del ds.units
            self.assertEqual(ds.units, None)

        with h5rdmtoolbox.File() as h5:
            with self.assertRaises(title.TitleError):
                h5.title = ' test'
            with self.assertRaises(title.TitleError):
                h5.title = 'test '
            with self.assertRaises(title.TitleError):
                h5.title = '9test'
            h5.title = 'test'
            self.assertEqual(h5.title, 'test')
            del h5.title
            self.assertEqual(h5.title, None)

    def test_title(self):
        """Test title attribute"""
        h5rdmtoolbox.use('tbx')
        with h5rdmtoolbox.File() as h5:
            with self.assertRaises(title.TitleError):
                h5.title = ' test'
            with self.assertRaises(title.TitleError):
                h5.title = 'test '
            with self.assertRaises(title.TitleError):
                h5.title = '9test'
            h5.title = 'test'
            self.assertEqual(h5.title, 'test')
            del h5.title
            self.assertEqual(h5.title, None)

    def test_source(self):
        h5tbx.use('tbx')

        htwr = conventions.source.Hardware(device='PressureSensorX',
                                           manufacturer='PressureCompany',
                                           serial_number='1234567890',
                                           description='Pressure senor for testing',
                                           temperature_range=[0, 50],
                                           temperature_range_unit=['C', 'C'])
        self.assertEqual(htwr.device, 'PressureSensorX')
        self.assertEqual(htwr.manufacturer, 'PressureCompany')
        self.assertEqual(htwr.serial_number, '1234567890')
        self.assertEqual(htwr.description, 'Pressure senor for testing')
        self.assertEqual(htwr.temperature_range, [0, 50])
        self.assertEqual(htwr.temperature_range_unit, ['C', 'C'])
        self.assertEqual(sorted(htwr.required_items()),
                         sorted([('device', 'PressureSensorX'),
                                 ('manufacturer', 'PressureCompany'),
                                 ('serial_number', '1234567890')]))
        self.assertEqual(htwr._pattern, '^[0-9].*')
        self.assertEqual(sorted(htwr.optional_items()),
                         sorted([('description', 'Pressure senor for testing'),
                                 ('temperature_range', [0, 50]),
                                 ('temperature_range_unit', ['C', 'C'])]))

        with h5rdmtoolbox.File() as h5:
            h5.create_dataset('test', data=[1, 2, 3],
                              source=htwr, units='m', long_name='test')
            self.assertIsInstance(h5['test'].source, conventions.source.Hardware)

        with self.assertRaises(ValueError):
            conventions.source.Hardware(device='1PressureSensorX',
                                        manufacturer='PressureCompany',
                                        serial_number='1234567890',
                                        description='Pressure senor for testing',
                                        temperature_range=[0, 50],
                                        temperature_range_unit=['C', 'C'])

        with self.assertRaises(ValueError):
            conventions.source.Hardware(device=None,
                                        manufacturer='PressureCompany',
                                        serial_number='1234567890',
                                        description='Pressure senor for testing',
                                        temperature_range=[0, 50],
                                        temperature_range_unit=['C', 'C'])

        sftw = conventions.source.Software(name='h5rdmtoolbox',
                                           version='1.0',
                                           url='https://h5rdmtoolbox.readthedocs.io/en/latest/',
                                           description='This is my software')
        self.assertEqual(sftw.name, 'h5rdmtoolbox')
        self.assertEqual(sftw.version, version.Version('1.0'))
        self.assertEqual(sftw.url, 'https://h5rdmtoolbox.readthedocs.io/en/latest/')
        self.assertEqual(sftw.description, 'This is my software')
        self.assertEqual(sorted(sftw.required_items()),
                         sorted([('name', 'h5rdmtoolbox'),
                                 ('version', version.Version('1.0')),
                                 ('description', 'This is my software'),
                                 ('url', 'https://h5rdmtoolbox.readthedocs.io/en/latest/')]))
        self.assertEqual(sorted(sftw.optional_items()),
                         sorted([('author', None),
                                 ('license', None),
                                 ('language', None),
                                 ('platform', None)]))
        self.assertEqual(sftw._pattern, '^[0-9].*')

        with self.assertRaises(ValueError):
            conventions.source.Software(name='1h5rdmtoolbox',
                                        version='1.0',
                                        url='https://h5rdmtoolbox.readthedocs.io/en/latest/',
                                        description='This is my software')

        with self.assertRaises(ValueError):
            conventions.source.Software(name='1h5rdmtoolbox',
                                        version='1.0',
                                        url='ww.h5rmtoolbox.de',
                                        description='This is my software')

        with h5rdmtoolbox.File() as h5:
            ds1 = h5.create_dataset('test1', data=[1, 2, 3], units='m', long_name='test')
            ds2 = h5.create_dataset('test2', data=[1, 2, 3], units='m', long_name='test',
                                    source=sftw)
            self.assertEqual(ds1.source, None)
            self.assertEqual(ds2.source, sftw)

            h5tbx.use(None)
            h5.create_dataset('test3', data=[1, 2, 3], attrs={'source': None})
            h5.create_dataset('test4', data=[1, 2, 3], attrs={'source': {'name': 'h5rdmtoolbox'}})
            h5.create_dataset('test5', data=[1, 2, 3], attrs={'source': 1.5})
            h5tbx.use('tbx')
            with self.assertRaises(RuntimeError):
                print(h5.test3.source)
            with self.assertRaises(ValueError):
                print(h5.test4.source)
            with self.assertRaises(RuntimeError):
                print(h5.test5.source)
            h5.test5.source = sftw
            self.assertIsInstance(h5.test5.source, conventions.source.Software)

    def test_standard_name(self):
        sn_fail = standard_name.StandardName(name='', canonical_units='m')
        with self.assertRaises(standard_name.StandardNameError):
            sn_fail.check_syntax()
        sn_fail = standard_name.StandardName(name=' x', canonical_units='m')
        with self.assertRaises(standard_name.StandardNameError):
            sn_fail.check_syntax()
        sn_fail = standard_name.StandardName(name='x ', canonical_units='m')
        with self.assertRaises(standard_name.StandardNameError):
            sn_fail.check_syntax()
        sn_fail = standard_name.StandardName(name='x_coordinate_$', canonical_units='m')
        with self.assertRaises(standard_name.StandardNameError):
            sn_fail.check_syntax()
        sn_fail = standard_name.StandardName(name='1x_coordinate', canonical_units='m')
        with self.assertRaises(standard_name.StandardNameError):
            sn_fail.check_syntax()

        sn1 = standard_name.StandardName(name='acc',
                                         description=None,
                                         canonical_units='m**2/s',
                                         snt=None)
        self.assertEqual(sn1.canonical_units, 'm**2/s')
        self.assertEqual(sn1.units, 'm**2/s')

        with self.assertRaises(KeyError):
            tutorial.get_standard_name_table()['z_coord']

        with self.assertRaises(KeyError):
            standard_name.StandardName.from_snt('xx_coordinate', snt=tutorial.get_standard_name_table())

        sn = standard_name.StandardName.from_snt('x_coordinate', snt=tutorial.get_standard_name_table())
        sn.check_syntax()
        self.assertEqual(sn.canonical_units, 'm')
        self.assertEqual(sn.name, 'x_coordinate')
        self.assertEqual(sn.description, 'x indicates the component in x-axis direction')

        sn2 = standard_name.StandardName(name='acc',
                                         description=None,
                                         canonical_units='m^2/s',
                                         snt=None)
        self.assertEqual(sn2.canonical_units, 'm**2/s')

        sn3 = standard_name.StandardName(name='acc',
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
        _ = standard_name.StandardName(name='a',
                                       description=None,
                                       canonical_units='m^2/s',
                                       snt=None)

        sn5 = standard_name.StandardName(name='a',
                                         description=None,
                                         canonical_units='m-2/s',
                                         snt=None)
        self.assertEqual(sn5.canonical_units, '1/m**2/s')

        self.assertTrue(sn1 != sn3)

    def test_validversion(self):
        self.assertTrue(IsValidVersionString()('v0.1.0'))
        self.assertFalse(IsValidVersionString()('a.b.c'))

    def test_validunit(self):
        self.assertTrue(IsValidUnit()('m/s'))
        self.assertTrue(IsValidUnit()('1 m/s'))
        self.assertFalse(IsValidUnit()('hello/world'))

    def test_responsible_person(self):
        orcid = '0000-0001-8729-0482'
        self.assertTrue(conventions.respuser.is_valid_orcid_pattern(orcid))
        self.assertFalse(conventions.respuser.is_valid_orcid_pattern('123-123-123-123'))
        self.assertFalse(conventions.respuser.is_valid_orcid_pattern(orcid[0:-1]))
        self.assertTrue(conventions.respuser.exist(orcid))
        not_existing_orcid = '0000-0001-5747-0739'
        self.assertFalse(conventions.respuser.exist(not_existing_orcid))


    def test_translation_table(self):
        translation = standard_name.StandardNameTableTranslation('pytest', {'u': 'x_velocity'})
        self.assertIsInstance(translation, standard_name.StandardNameTableTranslation)
        self.assertDictEqual(translation.translation_dict, {'u': 'x_velocity'})
        snt = standard_name.StandardNameTable.load_registered('Test-v1')
        translation.register(snt, overwrite=True)
        standard_name.StandardNameTableTranslation.print_registered()
        del translation
        translation = standard_name.StandardNameTableTranslation.load_registered('test-to-Test-v1')
        self.assertIsInstance(translation, standard_name.StandardNameTableTranslation)
        self.assertIsInstance(translation.translation_dict, DictConfig)

    def test_StandardNameTableFromYaml(self):
        table = standard_name.StandardNameTable.from_yaml(testdir / 'sntable.yml')
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
        table = standard_name.StandardNameTable.from_yaml(testdir / 'sntable_with_split.yml')
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
        self.assertIsInstance(table['particle_image'], standard_name.StandardName)

    def test_StandardNameTableFromWeb(self):
        cf = standard_name.StandardNameTable.from_web(
            url='https://cfconventions.org/Data/cf-standard-names/79/src/cf-standard-name-table.xml',
            name='standard_name_table')
        self.assertEqual(cf.name, 'standard_name_table')
        self.assertEqual(cf.versionname, 'standard_name_table-v79')
        self.assertTrue(standard_name.check_url(cf.url))
        self.assertFalse(standard_name.check_url(cf.url + '123'))

        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            connected = False
            warnings.warn('Cannot check Standard name table from '
                          f'gitlab: {e}')
        if connected:
            opencefa = standard_name.StandardNameTable.from_gitlab(url='https://git.scc.kit.edu',
                                                                   file_path='open_centrifugal_fan_database-v1.yaml',
                                                                   project_id='35443',
                                                                   ref_name='main')
            self.assertEqual(opencefa.name, 'open_centrifugal_fan_database')
            self.assertEqual(opencefa.versionname, 'open_centrifugal_fan_database-v1')

    def test_from_yaml(self):
        table = standard_name.StandardNameTable.from_yaml(testdir / 'sntable.yml')
        self.assertIsInstance(table.filename, pathlib.Path)
        self.assertIsInstance(table['synthetic_particle_image'], standard_name.StandardName)

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

        snttrans = standard_name.StandardNameTableTranslation('test', {'images': 'invalid_synthetic_particle_image'})
        with self.assertRaises(KeyError):
            snttrans.verify(table)

        snttrans = standard_name.StandardNameTableTranslation('test', {'images': 'synthetic_particle_image'})
        self.assertTrue(snttrans.verify(table))

        self.assertEqual(snttrans.translate('images'), 'synthetic_particle_image')

        yaml_filename = table.to_yaml(generate_temporary_filename(suffix='.yml'))
        table2 = standard_name.StandardNameTable.from_yaml(yaml_filename)
        self.assertEqual(table, table2)
        table2.set('other', 'desc', 'm')
        self.assertNotEqual(table, table2)

    def test_translate_group(self):
        h5tbx.use('tbx')
        with h5tbx.File(standard_name_table=tutorial.get_standard_name_table()) as h5:
            ds1 = h5.create_dataset('ds1', shape=(2,), units='m', long_name='a long name')
            ds2 = h5.create_dataset('/grp/ds2', shape=(2,), units='m', long_name='a long name')
            translation = {'ds1': 'x_coordinate', 'ds2': 'y_coordinate'}
            sntt = standard_name.StandardNameTableTranslation('test', translation)
            sntt.translate_group(h5)
            self.assertEqual(ds1.standard_name, 'x_coordinate')
            self.assertEqual(ds2.standard_name, 'y_coordinate')

    def test_merge(self):
        registered_snts = standard_name.StandardNameTable.get_registered()
        new_snt = standard_name.merge(registered_snts, name='newtable', institution=None,
                                      version_number=1, contact='matthias.probst@kit.edu')
        self.assertTrue(new_snt.name, 'newtable')

    def test_empty_SNT(self):
        snt = standard_name.StandardNameTable('test_snt',
                                              table=None,
                                              version_number=1,
                                              institution='my_institution',
                                              contact='mycontact@gmail.com')
        self.assertIsInstance(snt.table, dict)
        self.assertEqual(snt.filename, None)

    def test_wrong_contact(self):
        with self.assertRaises(ValueError):
            standard_name.StandardNameTable('test_snt',
                                            table=None,
                                            version_number=1,
                                            institution='my_institution',
                                            contact='mycontact')
