import pathlib
import requests
import shutil
import unittest
import warnings
import yaml

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions import core
from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable


class TestConventions(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

    def test_getattr(self):
        with h5tbx.use('h5tbx') as cv:
            isinstance(cv, h5tbx.conventions.Convention)
            with h5tbx.File() as h5:
                h5.create_dataset('test', data=1, units='m/s')
                self.assertEqual('m/s', str(h5.test.units))

    def test_overload_standard_attributes(self):
        yaml_filename = h5tbx.tutorial.get_standard_attribute_yaml_filename()
        cv = h5tbx.conventions.Convention.from_yaml(yaml_filename)
        self.assertTupleEqual(('scale_and_offset',), cv.decoders)
        self.assertIn('comment', cv.properties[h5tbx.File])
        self.assertIn('comment', cv.properties[h5tbx.Group])

    def test_add_decoder(self):
        h5tbx.use('h5tbx')
        cv = h5tbx.conventions.get_current_convention()

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

    def test_standard_name_table_as_relative_filename(self):
        snt_filename = h5tbx.tutorial.get_standard_name_table_yaml_file()

        yaml_filename = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        # copy to the same directory
        shutil.copy(snt_filename, yaml_filename.parent / snt_filename.name)

        sa_dict = {'__name__': 'standard_name_table',
                   '__institution__': 'https://orcid.org/members/001G000001e5aUTIAY',
                   '__contact__': 'https://orcid.org/0000-0001-8729-0482',
                   '__use_scale_offset__': True,
                   'standard_name_table':
                       {
                           'target_method': '__init__',
                           'validator': {'$standard_name_table': f'relpath({snt_filename.name})'},
                           'default_value': f'relpath({snt_filename.name})',
                           'type_hint': 'StandardNameTable',
                           'description': 'A standard name table'
                       }
                   }
        with open(yaml_filename, 'w') as f:
            yaml.safe_dump(sa_dict, f)

        local_cv = h5tbx.conventions.Convention.from_yaml(yaml_filename)
        local_cv.register()
        with h5tbx.use(local_cv.name):
            with h5tbx.File() as h5:
                self.assertIsInstance(h5.standard_name_table, StandardNameTable)

    def test_process_paths(self):
        __this_dir__ = pathlib.Path(__file__).parent
        abspath = str((__this_dir__ / 'a/path/').absolute())

        self.assertEqual({'a': []}, core._process_paths({'a': []}, __this_dir__))
        self.assertEqual([], core._process_paths([], __this_dir__))
        self.assertEqual(3.4, core._process_paths(3.4, __this_dir__))
        self.assertEqual('a/path/', core._process_paths('a/path/', __this_dir__))
        self.assertEqual(abspath, core._process_paths('relpath(a/path/)', __this_dir__))
        self.assertEqual({'a': 2}, core._process_paths({'a': 2}, __this_dir__))
        self.assertEqual({'a': 2, 'b': {'c': 'a/path/'}},
                         core._process_paths({'a': 2, 'b': {'c': 'a/path/'}}, __this_dir__))
        self.assertEqual({'a': 2, 'b': {'c': abspath}},
                         core._process_paths({'a': 2, 'b': {'c': 'relpath(a/path/)'}}, __this_dir__))

    def test_use(self):
        h5tbx.use(h5tbx.get_config()['default_convention'])
        self.assertEqual(h5tbx.conventions.get_current_convention().name, h5tbx.get_config()['default_convention'])
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5py')
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual('using("h5py")', h5tbx.use(None).__repr__())
        self.assertEqual('using("h5py")', h5tbx.use('h5py').__repr__())
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5py')
        h5tbx.use('h5tbx')
        self.assertEqual('using("h5tbx")', h5tbx.use('h5tbx').__repr__())
        self.assertEqual('using("h5tbx")', h5tbx.use('h5tbx').__repr__())
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('invalid_convention')

    def test_from_yaml(self):
        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""name: test""")
        with self.assertRaises(ValueError):
            h5tbx.conventions.from_yaml(f.name)
        with self.assertRaises(ValueError):
            h5tbx.conventions.Convention.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""__name__: test""")
        with self.assertRaises(ValueError):
            h5tbx.conventions.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        cv = h5tbx.conventions.from_yaml(f.name)
        self.assertEqual(cv.name, 'test')
        self.assertEqual(cv.contact, 'me')

        cv = h5tbx.conventions.Convention.from_yaml(f.name)
        self.assertEqual(cv.name, 'test')
        self.assertEqual(cv.contact, 'me')

        f1 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        f2 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        with open(f1, 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        test_std_attr = {'title': {'validator': {'$regex': '^[A-Z].*(?<!\s)$'},
                                   'target_methods': '__init__',
                                   'description': 'This is a test', }
                         }
        with open(f2, 'w') as f:
            yaml.safe_dump(test_std_attr, f)

        with self.assertRaises(ValueError):
            h5tbx.conventions.from_yaml([f1, f2])

    def test_cv_h5tbx(self):
        h5tbx.use(None)
        self.assertTupleEqual((), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use('h5tbx')
        self.assertTupleEqual(('scale_and_offset',), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use(None)
        self.assertTupleEqual((), h5tbx.wrapper.ds_decoder.decoder_names)
        h5tbx.use('h5tbx')
        self.assertTupleEqual(('scale_and_offset',), h5tbx.wrapper.ds_decoder.decoder_names)

        with h5tbx.File() as h5:
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
            self.assertEqual(h5.convention, h5tbx.conventions.get_current_convention())
            self.assertEqual({}, h5.standard_attributes)
            ds = h5.create_dataset('test', data=1, units='m/s')
            self.assertEqual(sorted(['offset', 'scale', 'units', 'symbol']), sorted(ds.standard_attributes.keys()))
            self.assertEqual(ds.convention, h5tbx.conventions.get_current_convention())

    def test_del_standard_attribute(self):
        h5tbx.use('h5tbx')

        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=1, units='m/s', scale=3)
            self.assertEqual(1, int(ds.values[()]))
            self.assertEqual(3, int(ds[()]))

        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=1, units='m/s', scale='3')
            self.assertEqual(1, int(ds.values[()]))
            self.assertEqual(3, int(ds[()]))

        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=1, units='m/s', scale='3 1/s')
            self.assertEqual(1, int(ds.values[()]))
            self.assertEqual(3, int(ds[()]))
            self.assertEqual('m/s', str(ds.units))
            self.assertEqual('m/s**2', str(ds[()].attrs['units']))

        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=1, units='m/s', scale=3)
            with self.assertRaises(ValueError):
                del ds.scale
            self.assertTrue('scale' in ds.attrs)
            with h5tbx.set_config(allow_deleting_standard_attributes=True):
                del ds.scale
                self.assertTrue('scale' not in ds.attrs)

    def test_from_zenodo(self):
        if self.connected:
            # we can download from zenodo by passing the short or full DOI or the URL:

            dois = ('8301535', '10.5281/zenodo.8301535', 'https://zenodo.org/record/8301535',
                    'https://doi.org/10.5281/zenodo.8301535')
            h5tbx.UserDir.clear_cache()
            with self.assertRaises(ValueError):  # because it is not a standard attribute YAML file!
                cv = h5tbx.conventions.from_zenodo(doi=8266929)

            for doi in dois:
                cv = h5tbx.conventions.from_zenodo(doi=doi)
                self.assertEqual(cv.name, 'h5rdmtoolbox-tutorial-convention')

        cv = h5tbx.conventions.from_zenodo(doi=8301535)
        self.assertEqual(cv.name, 'h5rdmtoolbox-tutorial-convention')
        self.assertEqual(
            h5tbx.conventions.standard_attributes.DefaultValue.EMPTY,
            cv.properties[h5tbx.File]['data_type'].default_value
        )
        cv.properties[h5tbx.File]['data_type'].make_optional()
        self.assertEqual(
            h5tbx.conventions.standard_attributes.DefaultValue.NONE,
            cv.properties[h5tbx.File]['data_type'].default_value
        )

    def test_default_value(self):
        from h5rdmtoolbox.conventions.consts import DefaultValue
        d = DefaultValue('$none')
        self.assertEqual(d.value, DefaultValue.NONE)
        d = DefaultValue('$empty')
        self.assertEqual(d.value, DefaultValue.EMPTY)
