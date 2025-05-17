import logging
import pathlib
import shutil
import sys
import unittest
import warnings
from datetime import datetime

import h5py
import pint
import requests
import yaml
from ssnolib import StandardName, StandardNameTable

import h5rdmtoolbox
import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import convention, tutorial
from h5rdmtoolbox.convention import core
from h5rdmtoolbox.convention import yaml2jsonld
from h5rdmtoolbox.convention.core import InvalidAttribute, MissingAttribute
from h5rdmtoolbox.repository.zenodo import ZenodoSandboxDeposit
from h5rdmtoolbox.repository.zenodo.metadata import Metadata, Creator
from h5rdmtoolbox.tutorial import TutorialConventionZenodoRecordID

logger = logging.getLogger('h5rdmtoolbox')
# setting logger to debug:
logger.setLevel('DEBUG')
__this_dir__ = pathlib.Path(__file__).parent


class TestConventions(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://zenodo.org', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

    def test_yaml2jsonld(self):
        yaml_filename = tutorial.get_convention_yaml_filename()
        jsonld_filename = yaml2jsonld(yaml_filename)
        self.assertTrue(jsonld_filename.exists())

    def test_list_of_validators(self):
        lov = convention.get_list_of_validators()
        self.assertIsInstance(lov, dict)
        self.assertTrue(len(lov) > 0)

    def test_create_with_code(self):
        cv = convention.Convention(name='MyFirstConvention', contact='John Doe')
        cv.register()
        self.assertNotEqual(cv, convention.get_current_convention())
        h5tbx.use('MyFirstConvention')
        self.assertEqual(cv, convention.get_current_convention())

        from pydantic import BaseModel
        from typing_extensions import Literal

        PublicationType = Literal[
            "book",
            "conferencepaper",
            "article",
            "patent",
            "report",
            "other",
        ]

        class PublicationValidator(BaseModel):
            """Validate an orcid (a simple naive version)"""
            value: PublicationType

        # create a standard attribute:
        std_attr = h5tbx.convention.standard_attributes.StandardAttribute(
            name='publication_type',
            validator=PublicationValidator,
            target_method='__init__',
            description='Publication type',
            default_value='$empty'
        )
        cv.add_standard_attribute(std_attr)

        h5tbx.use(None)
        h5tbx.use(cv.name)
        with self.assertRaises(h5tbx.errors.StandardAttributeError):
            with h5tbx.File() as _:
                pass
        with h5tbx.File(publication_type='book') as h5:
            self.assertEqual(h5.attrs['publication_type'], 'book')
        h5tbx.use(None)

    def test_upload_convention(self):
        cv_yaml_filename = tutorial.get_convention_yaml_filename()
        self.assertTrue(cv_yaml_filename.exists())

        # upload to zenodo sandbox
        meta = Metadata(
            version="1.0.0",
            title='H5TBX Tutorial Convention Definition',
            description='The convention file used in tests and documentation as part of '
                        f'the h5rdmtoolbox={h5tbx.__version__}.',
            creators=[Creator(name="Probst, Matthias",
                              affiliation="Karlsruhe Institute of Technology, Institute for Thermal Turbomachinery",
                              orcid="0000-0001-8729-0482")],
            upload_type='other',
            access_right='open',
            keywords=['h5rdmtoolbox', 'tutorial', 'convention'],
            publication_date=datetime.now(),
        )
        zsr = ZenodoSandboxDeposit(source=None)
        zsr.metadata = meta
        zsr.upload_file(cv_yaml_filename, overwrite=True, metamapper=None)

        # zsr.publish()

        # download file from zenodo deposit:
        self.assertEqual(1, len(zsr.get_filenames()))

        filename = zsr.files.get('tutorial_convention.yaml').download()
        self.assertTrue(filename.exists())
        zsr.delete()

    def test_delete(self):
        cv = h5tbx.convention.Convention.from_yaml(__this_dir__ / 'simple_cv.yaml')
        self.assertTrue(cv.name in sys.modules)
        self.assertIn('simple_cv', h5tbx.convention.get_registered_conventions())
        cv.delete()
        self.assertFalse(cv.name in sys.modules)
        cv.delete()
        self.assertFalse(cv.name in sys.modules)
        self.assertNotIn('simple_cv', h5tbx.convention.get_registered_conventions())

    def test_extract_function_info(self):
        from h5rdmtoolbox.convention.generate import extract_function_info, validate_specialtype_functions
        import ast
        tree = ast.parse(" ")
        self.assertEqual(extract_function_info(tree), [])

        lines = """
def f1(a, b, c=3):
    pass
"""
        tree = ast.parse(lines)
        r = extract_function_info(tree)
        self.assertTrue(r[0][0] == 'f1')
        self.assertTrue(r[0][1] == ['a', 'b', 'c'])
        with self.assertRaises(ValueError):
            validate_specialtype_functions({r[0][0]: r[0][1]})

        lines = """
def validate_f1(a, b, c=3, d=2):
    pass"""
        tree = ast.parse(lines)
        r = extract_function_info(tree)
        with self.assertRaises(ValueError):
            validate_specialtype_functions({r[0][0]: r[0][1]})

    def test_h5tbx(self):
        f = h5tbx.UserDir['convention'] / 'h5tbx' / 'h5tbx.py'
        f.unlink(missing_ok=True)
        from h5rdmtoolbox.convention import build_convention
        build_convention()

        h5tbx.use('h5tbx')
        cv = h5tbx.convention.get_current_convention()

        self.assertEqual('h5tbx', h5tbx.convention.get_current_convention().name)

        with h5tbx.File(creation_mode='experimental') as h5:
            self.assertIsInstance(h5.creation_mode, type(h5.creation_mode))
            ds = h5.create_dataset(name='ds', data=3.4, units='m/s', symbol='U')
            self.assertEqual(ds.symbol, 'U')
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                _ = h5.create_dataset(name='ds2', data=3.4, units='3.4', symbol='U')

            with self.assertRaises(ValueError):
                _ = h5.create_dataset(name='ds', data=3.4, units='V', symbol='U')

            self.assertIsInstance(ds.units, pint.Unit)
            self.assertIsInstance(ds.symbol, str)
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                ds.symbol = 1.4
            self.assertEqual(ds.symbol, 'U')
            ds.symbol = 'P'
            self.assertEqual(ds.symbol, 'P')
            self.assertEqual(str(ds.units), 'm/s')
            ds.units = h5tbx.get_ureg().Unit('N m')
            self.assertEqual(str(ds.units), 'N*m')

        h5tbx.use(None)
        self.assertEqual('h5py', h5tbx.convention.get_current_convention().name)

    def test_getattr(self):
        h5tbx.use(None)
        self.assertEqual('h5py', h5tbx.convention.get_current_convention().name)
        with h5tbx.use('h5tbx') as cv:
            isinstance(cv, h5tbx.convention.Convention)
            with h5tbx.File(creation_mode='experimental') as h5:
                h5.create_dataset('test', data=1, units='m/s')
                self.assertEqual('m/s', str(h5.test.units))
        self.assertEqual('h5py', h5tbx.convention.get_current_convention().name)

    def test_overload_standard_attributes(self):
        yaml_filename = h5tbx.tutorial.get_convention_yaml_filename()
        cv = h5tbx.convention.Convention.from_yaml(yaml_filename, overwrite=True)
        self.assertIsInstance(cv, h5tbx.convention.Convention)
        self.assertTupleEqual(('scale_and_offset',), cv.decoders)
        self.assertIn('comment', cv.properties[h5tbx.File])
        self.assertIn('comment', cv.properties[h5tbx.Group])

    def test_overwrite_existing_file(self):
        if self.connected:
            # delete an existing convention like this first:
            cv = h5tbx.convention.from_zenodo(doi_or_recid=TutorialConventionZenodoRecordID,
                                              overwrite=False,
                                              force_download=True)
            self.assertEqual(cv.name, 'h5rdmtoolbox-tutorial-convention')
            h5tbx.use('h5rdmtoolbox-tutorial-convention')

            with h5tbx.File(mode='w',
                            attrs=dict(
                                data_type='experimental',
                                contact='https://orcid.org/0000-0001-8729-0482'),
                            comment='Root comment') as h5:
                h5.create_group('g1', comment='Group comment')
                h5.create_dataset('g1/ds1', data=1, comment='Dataset comment', long_name="dataset 1")
                self.assertEqual(h5.attrs['comment'], 'Root comment')
                self.assertEqual(h5.comment, 'Root comment')
                self.assertEqual(h5.comment, 'Root comment')
                self.assertEqual(h5.g1.attrs['comment'], 'Group comment')
                self.assertEqual(h5.g1.comment, 'Group comment')
                self.assertEqual(h5.g1.ds1.attrs['comment'], 'Dataset comment')
                self.assertEqual(h5.g1.ds1.comment, 'Dataset comment')

                self.assertTrue('contact' in h5.attrs)
                self.assertEqual(str(h5.contact), 'https://orcid.org/0000-0001-8729-0482')
                self.assertTrue('data_type' in h5.attrs)
                self.assertEqual(str(h5.data_type), 'experimental')
                self.assertEqual(str(h5.attrs['data_type']), 'experimental')

            filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
            with h5py.File(filename, 'w') as h5:
                h5.attrs['data_type'] = 'invalid'
            with h5tbx.File(filename) as h5:
                with h5tbx.set_config(ignore_get_std_attr_err=True):
                    with self.assertWarns(h5tbx.errors.StandardAttributeValidationWarning):
                        h5.data_type
                with h5tbx.set_config(ignore_get_std_attr_err=False):
                    with self.assertRaises(h5tbx.errors.StandardAttributeError):
                        h5.data_type

            # there was a bug, that data was not correctly written to the file when an existing file was overwritten
            # so let's check that:
            with h5tbx.File(h5.hdf_filename, mode='w',
                            data_type='experimental',
                            contact='https://orcid.org/0000-0001-8729-0482') as h5:
                self.assertTrue('contact' in h5.attrs)
                self.assertTrue('data_type' in h5.attrs)

    def test_add_decoder(self):
        h5tbx.use('h5tbx')
        cv = h5tbx.convention.get_current_convention()

        def multiply_by_2_decoder(xarr, _):
            return xarr * 2

        h5tbx.register_dataset_decoder(multiply_by_2_decoder)
        with self.assertRaises(TypeError):
            cv.add_decoder(2)
        with self.assertRaises(KeyError):
            cv.add_decoder('multiply_by_2')
        cv.add_decoder('multiply_by_2_decoder')

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, units='m/s')
            arr = h5['test'][()]
            self.assertEqual(1, arr)

        # reload convention:
        h5tbx.use(None)
        h5tbx.use(cv)

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, units='m/s')
            arr = h5['test'][()]
            self.assertEqual(2, arr)

        def multiply_by_2_decoder_v2(xarr, _):
            return xarr * 2

        with self.assertRaises(ValueError):
            h5tbx.register_dataset_decoder(multiply_by_2_decoder, decoder_name='multiply_by_2_decoder_v2')
        h5tbx.register_dataset_decoder(multiply_by_2_decoder_v2, decoder_name='multiply_by_2_decoder_v2')
        h5tbx.register_dataset_decoder(multiply_by_2_decoder_v2, decoder_name='multiply_by_2_decoder_v2',
                                       overwrite=True)
        cv.add_decoder('multiply_by_2_decoder_v2')

        h5tbx.use(None)
        h5tbx.use(cv)

        with h5tbx.File() as h5:
            h5.create_dataset('test', data=1, units='m/s')
            arr = h5['test'][()]
            self.assertEqual(4, arr)

        # remove decoders
        self.assertTrue('multiply_by_2_decoder' not in cv.remove_decoder('multiply_by_2_decoder'))
        self.assertTrue('multiply_by_2_decoder_v2' not in cv.remove_decoder('multiply_by_2_decoder_v2'))

    def test_process_paths(self):
        abspath = str((__this_dir__ / 'a/path/').absolute())

        self.assertEqual({'a': []}, core._process_paths({'a': []}, __this_dir__))
        self.assertEqual([], core._process_paths([], __this_dir__))
        self.assertEqual([abspath, abspath],
                         core._process_paths(['relpath(a/path/)', 'relpath(a/path/)'], __this_dir__))
        self.assertEqual(3.4, core._process_paths(3.4, __this_dir__))
        self.assertEqual('a/path/', core._process_paths('a/path/', __this_dir__))
        self.assertEqual(abspath, core._process_paths('relpath(a/path/)', __this_dir__))
        self.assertEqual({'a': 2}, core._process_paths({'a': 2}, __this_dir__))
        self.assertEqual({'a': 2, 'b': {'c': 'a/path/'}},
                         core._process_paths({'a': 2, 'b': {'c': 'a/path/'}}, __this_dir__))
        self.assertEqual({'a': 2, 'b': {'c': abspath}},
                         core._process_paths({'a': 2, 'b': {'c': 'relpath(a/path/)'}}, __this_dir__))

    def test_use(self):
        h5tbx.use(None)
        self.assertEqual(h5tbx.convention.get_current_convention().name, 'h5py')
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual('using("h5py")', h5tbx.use(None).__repr__())
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual(h5tbx.convention.get_current_convention().name, 'h5py')
        h5tbx.use('h5tbx')
        self.assertEqual('using("h5tbx")', h5tbx.use('h5tbx').__repr__())
        self.assertEqual('using("h5tbx")', h5tbx.use('h5tbx').__repr__())
        self.assertEqual(h5tbx.convention.get_current_convention().name, 'h5tbx')
        with self.assertRaises(h5rdmtoolbox.errors.ConventionNotFound):
            h5tbx.use('invalid_convention')

    def test_from_yaml(self):
        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""name: test""")
        with self.assertRaises(ValueError):
            h5tbx.convention.from_yaml(f.name)
        with self.assertRaises(ValueError):
            h5tbx.convention.Convention.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""__name__: test""")
        with self.assertRaises(ValueError):
            h5tbx.convention.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        cv = h5tbx.convention.from_yaml(f.name, overwrite=False)
        cv = h5tbx.convention.from_yaml(f.name, overwrite=True)
        self.assertEqual(cv.name, 'test')
        self.assertEqual(cv.contact, 'me')

        cv = h5tbx.convention.Convention.from_yaml(f.name, overwrite=True)
        self.assertEqual(cv.name, 'test')
        self.assertEqual(cv.contact, 'me')

        f1 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        f2 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        with open(f1, 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        test_std_attr = {'title': {'validator': {'$regex': r'^[A-Z].*(?<!\s)$'},
                                   'target_methods': '__init__',
                                   'description': 'This is a test', }
                         }
        with open(f2, 'w') as f:
            yaml.safe_dump(test_std_attr, f)

        with self.assertRaises(TypeError):
            h5tbx.convention.from_yaml([f1, f2])

    def test_cv_h5tbx(self):
        h5tbx.use(None)
        self.assertTupleEqual((), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use('h5tbx')
        self.assertTupleEqual(('scale_and_offset',), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use(None)
        self.assertTupleEqual((), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use('h5tbx')
        self.assertTupleEqual(('scale_and_offset',), h5tbx.wrapper.ds_decoder.decoder_names)

        with h5tbx.File(creation_mode='experimental') as h5:
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                h5.create_dataset('test', data=1)
            h5.create_dataset('test', data=1, units='m/s')
            self.assertEqual('m/s', str(h5['test'].attrs['units']))
        h5tbx.use(None)

    def test_skwars_kwargs(self):
        """passing units in attrs and kwargs"""
        h5tbx.use('h5tbx')
        with h5tbx.File() as h5:
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                ds = h5.create_dataset('test', data=1, units='m/s', attrs={'units': 'Pa'})
            ds = h5.create_dataset('test', data=1, units='m/s')
            self.assertEqual('m/s', str(ds.attrs['units']))
            ds = h5.create_dataset('test2', data=1, units='m/s', attrs={'scale': 2})
            self.assertEqual(2, ds.attrs['scale'])

    def test_convention_file_props(self):
        h5tbx.use('h5tbx')
        with h5tbx.File() as h5:
            self.assertEqual(h5.convention, h5tbx.convention.get_current_convention())
            self.assertEqual(sorted(['creation_mode', ]), sorted(list(h5.standard_attributes)))
            ds = h5.create_dataset('test', data=1, units='m/s')
            self.assertEqual(sorted(['units', 'symbol']), sorted(ds.standard_attributes.keys()))
            self.assertEqual(ds.convention, h5tbx.convention.get_current_convention())

    def test_data_scale_and_offset(self):
        h5tbx.use('h5tbx')

        with h5tbx.File() as h5:
            ds_scale = h5.create_dataset('test_scale', data=1, units='m/s/V')

            ds = h5.create_dataset('test', data=1, units='V')
            ds.attach_data_scale_and_offset(ds_scale, None)

            self.assertEqual(ds.get_data_scale(), ds_scale)
            self.assertEqual(ds.get_data_offset(), None)

            self.assertEqual(ds[()].units, 'm/s')

        with h5tbx.File() as h5:
            ds_offset = h5.create_dataset('test_offset', data=1, units='m/s/V')

            ds = h5.create_dataset('test', data=1, units='V')
            with self.assertRaises(ValueError):
                ds.attach_data_scale_and_offset(None, ds_offset)

        with h5tbx.File() as h5:
            ds_offset = h5.create_dataset('test_offset', data=0.5, units='m/s')

            ds = h5.create_dataset('test', data=2.3, units='m/s')
            ds.attach_data_scale_and_offset(None, ds_offset)

            self.assertEqual(ds.get_data_scale(), None)
            self.assertEqual(str(ds.get_data_offset().attrs['units']), 'm/s')

            self.assertEqual(ds[()].units, 'm/s')
            self.assertEqual(float(ds[()].data), 2.3 + 0.5)

        with h5tbx.File() as h5:
            ds_offset = h5.create_dataset('test_offset', data=0.5, units='km/s')

            ds = h5.create_dataset('test', data=1, units='m/s')
            ds.attach_data_scale_and_offset(None, ds_offset)

            self.assertEqual(ds.get_data_scale(), None)
            self.assertEqual(str(ds.get_data_offset().attrs['units']), 'km/s')

            self.assertEqual(ds[()].units, 'm/s')
            self.assertEqual(float(ds[()].data), 1 + 500.)

        with h5tbx.File() as h5:
            ds_offset = h5.create_dataset('test_offset', data=1, units='km/s')

            ds_scale = h5.create_dataset('test_scale', data=1, units='m/s/V')

            ds = h5.create_dataset('test', data=1, units='V')
            ds.attach_data_scale_and_offset(ds_scale, ds_offset)

            self.assertEqual(ds.get_data_scale().attrs['units'], h5tbx.get_ureg().Unit('m/s/V'))
            self.assertEqual(str(ds.get_data_offset().attrs['units']), 'km/s')

            self.assertEqual(ds[()].units, 'm/s')
            self.assertEqual(float(ds[()].data), 1 + 1000)

    def test_from_zenodo(self):
        if self.connected:
            # delete an existing convention like this first:
            _ddir = h5tbx.UserDir['convention'] / 'h5rdmtoolbox_tutorial_convention'
            if _ddir.exists():
                shutil.rmtree(_ddir)
            h5tbx.convention.from_zenodo(doi_or_recid=TutorialConventionZenodoRecordID, force_download=True)

            h5tbx.use('h5rdmtoolbox-tutorial-convention')

            cv = h5tbx.convention.get_current_convention()
            self.assertEqual(cv.name, 'h5rdmtoolbox-tutorial-convention')
            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                h5.comment = 'This is a comment'
                self.assertEqual(h5.comment, 'This is a comment')

                with self.assertRaises(h5tbx.errors.StandardAttributeError):
                    h5.comment = '1.2 comment'

                h5.create_group('grp', comment='Group comment')
                self.assertEqual(h5['grp'].comment, 'Group comment')

                h5.create_dataset('test', data=4.3, standard_name='xx_reynolds_stress', units='m**2/s**2')
                self.assertEqual(str(h5['test'].standard_name), 'xx_reynolds_stress')
                self.assertEqual(h5['test'].attrs.raw["standard_name"], 'xx_reynolds_stress')
                self.assertIsInstance(h5['test'].standard_name, StandardName)
                h5.contact  # takes a bit because validated online!
                snt = h5.standard_name_table
                self.assertIsInstance(snt, StandardNameTable)
                for sa in h5.standard_attributes:
                    self.assertFalse('-' in sa)
                self.assertNotEqual(h5.standard_attributes['comment'].description,
                                    h5['test'].standard_attributes['comment'].description)

    def test_standard_name_table_as_file(self):
        cv = h5tbx.Convention.from_yaml(
            __this_dir__ / "test_convention.yaml",
            overwrite=True
        )
        h5tbx.use(cv)
        snt_file = __this_dir__ / "fan_standard_name_table.jsonld"
        with h5tbx.File(
                data_type='experimental',
                contact=h5tbx.__author_orcid__,
                standard_name_table=f"file://{snt_file}") as h5:
            isinstance(h5.standard_name_table, StandardNameTable)

    def test_alternative_attribute(self):
        h5tbx.Convention.from_yaml(tutorial.get_convention_yaml_filename(), overwrite=True)
        with h5tbx.use('h5rdmtoolbox-tutorial-convention'):
            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                with self.assertRaises(h5tbx.errors.StandardAttributeError):
                    h5.create_dataset('u', data=0.0, units='m/s')
                ds = h5.create_dataset("u", data=0.0, long_name="x-velocity")
                self.assertEqual(ds.long_name, "x-velocity")

    def test_standard_attributes_and_rdf(self):
        h5tbx.Convention.from_yaml(tutorial.get_convention_yaml_filename(), overwrite=True)
        with h5tbx.use('h5rdmtoolbox-tutorial-convention'):
            with h5tbx.File(
                    data_type=h5tbx.Attribute(
                        value="experimental",
                        frdf_object="https://www.wikidata.org/wiki/Q101965"),
                    contact=h5tbx.__author_orcid__,
                    title="test file") as h5:
                self.assertEqual(h5.title, "test file")
                self.assertEqual(h5.frdf['title'].predicate, 'https://schema.org/title')
                self.assertEqual(h5.data_type, "experimental")
                self.assertEqual(h5.frdf['data_type'].object, 'https://www.wikidata.org/wiki/Q101965')
                self.assertEqual(h5.rdf['data_type'].object, None)

    def test_default_value(self):
        from h5rdmtoolbox.convention.consts import DefaultValue
        d = DefaultValue('$none')
        self.assertEqual(d.value, DefaultValue.NONE)
        d = DefaultValue('$empty')
        self.assertEqual(d.value, DefaultValue.EMPTY)

    def test_validate_convention(self):
        cv = h5tbx.convention.Convention.from_yaml(__this_dir__ / 'simple_cv.yaml')
        cv.register()
        # units is default for all dataset, but not for string datasets!
        h5tbx.use(cv)
        with h5tbx.File() as h5:
            h5.create_string_dataset('ds_str', data='a string')
            h5.create_dataset('ds_int', data=123, units='m/s')
        cv.validate(h5.hdf_filename)

        h5py_filename = h5tbx.utils.generate_temporary_filename(suffix='.hdf')
        with h5py.File(h5py_filename, 'w') as h52:
            ds = h52.create_dataset('ds_float', data=123.1)
            ds.attrs['units'] = 'invalid'

        cv.validate(h5py_filename)

    def test_InvalidAttribute(self):
        ia = InvalidAttribute('/vel', 'units', 'invalid', 'Oups, wrong!')
        self.assertEqual(str(ia), 'Attribute "units" in "/vel" has an '
                                  'invalid value "invalid". Error message: "Oups, wrong!"')

    def test_MissingAttribute(self):
        ma = MissingAttribute('/vel', 'units')
        self.assertEqual(str(ma), 'Attribute "units" is missing in "/vel".')

    def test_dates(self):
        cv = h5tbx.convention.from_yaml(
            __this_dir__ / 'date_convention.yaml', overwrite=True
        )
        h5tbx.use(cv)

        with h5tbx.File(list_of_dates=['22.12.2023', '23.12.2023']) as h5:
            self.assertIsInstance(h5.list_of_dates, list)
            self.assertEqual(h5.list_of_dates, [datetime(2023, 12, 22), datetime(2023, 12, 23)])

        with h5tbx.File(date='22.12.2023') as h5:
            self.assertIsInstance(h5.date, datetime)
            self.assertEqual(h5.date, datetime(2023, 12, 22))

        with self.assertRaises(h5tbx.errors.StandardAttributeError):
            with h5tbx.File(specific_date={'date': '22.12.invalid', 'dateType': 'Created'}) as h5:
                pass
        with self.assertRaises(h5tbx.errors.StandardAttributeError):
            with h5tbx.File(specific_date={'date': '22.12.2023', 'dateType': 'invalid'}) as h5:
                pass
        with h5tbx.File(specific_date={'date': '22.12.2023', 'dateType': 'Created'}) as h5:
            self.assertIsInstance(h5.specific_date.date, datetime)
            self.assertEqual(h5.specific_date.dateType, 'Created')

    def test_engmeta_example(self):
        cv = h5tbx.convention.from_yaml(__this_dir__ / 'EngMeta.yaml', overwrite=True)
        h5tbx.use(cv)
        self.assertEqual(h5tbx.convention.get_current_convention().name, cv.name)
        with h5tbx.File(contact=dict(name='Matthias Probst'),
                        creator=dict(name='Matthias Probst',
                                     id='https://orcid.org/0000-0001-8729-0482',
                                     role='Researcher'
                                     ),
                        pid=dict(id='123', type='other'),
                        title='Test file to demonstrate usage of EngMeta schema') as h5:
            contact = h5.contact
            self.assertEqual(contact.name, 'Matthias Probst')
            self.assertEqual(h5.creator.name, 'Matthias Probst')
            self.assertEqual(h5.creator.role, 'Researcher')
            self.assertEqual(h5.creator.id, 'https://orcid.org/0000-0001-8729-0482')
            self.assertEqual(h5.pid.id, '123')
            self.assertEqual(h5.pid.type, 'other')
        with self.assertRaises(h5tbx.errors.StandardAttributeError):
            with h5tbx.File(contact=dict(invalid='Matthias Probst'),
                            creator=dict(name='Matthias Probst',
                                         id='https://orcid.org/0000-0001-8729-0482',
                                         role='Researcher'
                                         ),
                            pid=dict(id='123', type='other'),
                            title='Test file to demonstrate usage of EngMeta schema') as h5:
                pass
        with self.assertRaises(h5tbx.errors.StandardAttributeError):
            with h5tbx.File(contact=dict(name=123),
                            creator=dict(name='Matthias Probst',
                                         id='https://orcid.org/0000-0001-8729-0482',
                                         role='Researcher'
                                         ),
                            pid=dict(id='123', type='other'),
                            title='Test file to demonstrate usage of EngMeta schema') as h5:
                pass

    def test_read_invalid_attribute(self):
        cv = h5tbx.convention.Convention.from_yaml(__this_dir__ / 'simple_cv.yaml', overwrite=True)
        # h5tbx.use(None)
        # with h5tbx.File() as h5:
        #     h5.create_dataset('ds', data=[1, 2], attrs=dict(units='invalid'))
        # with h5tbx.use(cv):
        #     with h5tbx.File(h5.hdf_filename) as h5:
        #         with h5tbx.set_config(ignore_get_std_attr_err=True):
        #             with self.assertWarns(h5tbx.warnings.StandardAttributeValidationWarning):
        #                 units = h5.ds.units
        #         self.assertEqual(units, 'invalid')
        # with h5tbx.use(None):
        #     with h5tbx.File(h5.hdf_filename) as h5:
        #         with self.assertRaises(AttributeError):
        #             _ = h5.ds.units
        #         units = h5.ds.attrs['units']
        #         self.assertEqual(units, 'invalid')

        with h5tbx.use('simple_cv'):
            with h5tbx.File(creator={'name': 'Joe'}) as h5:
                self.assertEqual(h5.creator.name, 'Joe')
                self.assertEqual(h5.creator.orcid, None)
            with h5tbx.File(creator={'name': 'Joe',
                                     'invalid': '123'}) as h5:
                self.assertEqual(h5.creator.name, 'Joe')
                self.assertEqual(h5.creator.orcid, None)
                with self.assertRaises(AttributeError):
                    self.assertEqual(h5.creator.invalid, '123')
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                with h5tbx.File(creator={'name': 'Joe',
                                         'orcid': '123'}) as h5:
                    pass
            with h5tbx.File(creator={'name': 'Joe',
                                     'orcid': h5tbx.__author_orcid__}) as h5:
                self.assertEqual(h5.creator.name, 'Joe')
                self.assertEqual(str(h5.creator.orcid), h5tbx.__author_orcid__)
