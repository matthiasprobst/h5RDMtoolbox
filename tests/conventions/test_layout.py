import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout import *
from h5rdmtoolbox.conventions.layout.validation import *
from h5rdmtoolbox.conventions.layout.validators import *


class TestLayout(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_layout_success_ratio(self):
        lay = Layout()
        with self.assertWarns(UserWarning):
            self.assertEqual(lay.success_ratio, 1.0)
        lay['/'].attrs['long_name'] = ...
        # with self.assertRaises(ValueError):
        #     lay.success_ratio
        with h5py.File(generate_temporary_filename(), 'w') as h5:
            with self.assertRaises(ValueError):
                self.assertEqual(lay.success_ratio, 1.0)

    def test_registry(self):
        reg = LayoutRegistry()
        self.assertIsInstance(reg, LayoutRegistry)
        self.assertIsInstance(reg.names, list)
        self.assertIsInstance(reg['tbx'], Layout)

        lay = reg['tbx']
        with h5tbx.File() as h5:
            lay.validate(h5)
            self.assertFalse(lay.is_validated)

            h5.attrs['title'] = 'This is a title'

            lay.validate(h5)
            lay.report()
            print(lay.get_failed_validations())
            self.assertFalse(lay.is_validated)

    def test_validators(self):
        e = Equal(1)
        self.assertTrue(e(1))
        self.assertFalse(e(0))

        vs = ValidString()
        self.assertTrue(vs('Comment'))
        self.assertFalse(vs(' invalid'))
        self.assertFalse(vs('0invalid'))

        e = Equal('*')
        self.assertTrue(e('dawd'))
        self.assertTrue(e(Ellipsis))

        i = In(1, 2, 3, optional=False)
        self.assertFalse(i.is_optional)
        self.assertTrue(i(1))
        self.assertTrue(i(2))
        self.assertTrue(i(3))
        self.assertFalse(i(4))

        with h5tbx.File() as h5:
            h5.create_group('group1')
            ei = ExistIn('group1')
            with self.assertRaises(TypeError):
                ei('group1')
            self.assertTrue(ei(h5))

    def test_attrs_1(self):
        lay = Layout()
        lay['/'].attrs['long_name'] = ...

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)  # the root group has no attribute long_name
            h5.attrs['long_name'] = 'a long name'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)  # the root group has no attribute long_name

    def test_attrs_2(self):
        lay = Layout()
        lay['/'].attrs['long_name'] = ...
        lay['/'].attrs['user'] = 'MP'

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
            h5.attrs['long_name'] = 'a long name'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            h5.attrs['user'] = '_MP'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            h5.attrs['user'] = 'MP'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_attrs_3(self):
        """specifying multiple attributes in one go is always an AND-connection"""
        lay = Layout()
        lay.specify_dataset(...).specify_attrs(
            dict(standard_name=..., units=...))  # every dataset in root must have sn and u
        lay.specify_dataset(...).specify_attrs(dict(long_name=...))  # every dataset in root must have sn and u

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

            h5.create_dataset('test', data=1)
            ds = h5.create_dataset('test2', data=1)
            ds.attrs['standard_name'] = 'a'
            ds.attrs['units'] = 'b'
            lay.validate(h5)
            self.assertEqual(lay.fails, 3)

            h5['test'].attrs['long_name'] = 'a'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

    def test_opt_units(self):
        from h5rdmtoolbox.conventions.layout.tbx import IsValidUnit
        lay = Layout()
        lay.specify_dataset(...).specify_attrs(dict(units=IsValidUnit(optional=True)))
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

            h5.create_dataset('test', data=1)

            h5['test'].attrs['units'] = 'invalid'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_contact(self):
        from h5rdmtoolbox.conventions.layout.tbx import IsValidContact
        lay = Layout()
        lay.specify_attrs(dict(contact=IsValidContact()))
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            h5.attrs['contact'] = 'invalid'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            h5.attrs['contact'] = 'https://orcid.org/0000-0001-8729-0482'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

            h5.attrs['contact'] = ['https://orcid.org/0000-0001-8729-0482',
                                   'https://orcid.org/0000-0001-8729-0482']
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_attrs_4(self):
        """specifying a dataset with unknown name but specific attributes"""
        lay = Layout()
        # every dataset must have a standard name
        lay.specify_dataset(...).specify_attrs(dict(standard_name=...))
        # this shall only be valid once (count=1):
        lay.specify_dataset(...).specify_attrs(dict(standard_name='x_velocity', units='m/s'), count=1)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

            h5.create_dataset('test', data=1)
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            h5['test'].attrs['standard_name'] = 'any sn'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            u = h5.create_dataset('u', data=1)
            u.attrs['standard_name'] = 'x_velocity'
            u.attrs['units'] = 'wrong unit'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            u.attrs['units'] = 'm/s'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

        lay = Layout()
        # every dataset must have a standard name
        lay.specify_dataset(...).specify_attrs(dict(standard_name=...))
        # this shall only be valid once (count=1):
        lay.specify_dataset(...).specify_attrs(dict(standard_name='x_velocity', units='m/s'), count=2)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

            h5.create_dataset('test', data=1)
            lay.validate(h5)
            self.assertEqual(lay.fails, 3)

            h5['test'].attrs['standard_name'] = 'any sn'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            u = h5.create_dataset('u', data=1)
            u.attrs['standard_name'] = 'x_velocity'
            u.attrs['units'] = 'wrong unit'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            u.attrs['units'] = 'm/s'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            h5.create_dataset('u2', data=1)
            # h5['u2'].attrs['standard_name'] = 'y_velocity'
            h5['u2'].attrs['units'] = 'm/s'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            h5['test'].attrs['standard_name'] = 'x_velocity'
            h5['test'].attrs['units'] = 'm/s'
            h5['u2'].attrs['standard_name'] = 'x_velocity'
            h5['u2'].attrs['units'] = 'm/s'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)  # there are 3 datasets with x_velocity, but only 2 are allowed

    def test_core(self):
        # init layout:
        lay = Layout()

        # specifications:
        # /group1
        #     -a: long_name=an_attribute
        # /group2
        g1 = lay.specify_group('group1')  # lay.add_Group(Equal('group1'))
        g2 = lay[Equal('group2')]

        # check types:
        self.assertIsInstance(g1, GroupValidation)
        self.assertIsInstance(g2, GroupValidation)

        self.assertIsInstance(g1.attrs, AttributeValidationManager)
        # g1.attrs.add(Equal('attr1'), Any())

        # add an attribute to group1, which MUST exist:
        g1.attrs.add('long_name', 'an_attribute')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            # group1 and group2 missing. attributes cannot be checked, thus 2 fails:
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # both groups are missing

            # now added group1, but still group2 is missing and now also attribute "long_name" missing
            g = h5.create_group('group1')
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # one group is missing and the other has no attribute long_name

            g.attrs['test'] = '2'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # one group is missing and the other has a wrong attribute

            g.attrs['long_name'] = '2'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # one group is missing and the other has a wrong attribute long_name

            g.attrs['long_name'] = 'an_attribute'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            # regex
            g1.attrs.add('coord', Regex(r'^[x-z]_coordinate$'))
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            g.attrs['coord'] = 'a_coordinate'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            g.attrs['coord'] = 'x_coordinate'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            g1.attrs.add(Regex('.*coord2.*'), Regex(r'^[x-z]_coordinate$'))
            g.attrs['coord2'] = 'x_coordinate'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            g.attrs['hellocoord2'] = 'a_coordinate'
            hdf_filename = h5.filename

            lay.validate(hdf_filename)
            self.assertEqual(lay.fails, 1)
            lay.print_validation_results()

        print(lay)

    def test_docs_example(self):
        lay = Layout()

        dv = lay['*'].specify_dataset(compression='gzip')
        lay['*'].specify_dataset().attrs['units'] = ...
        lay['*'].specify_group().attrs['comment'] = Regex(r'^[^ 0-9].*')

        lay['devices'].attrs.add('long_name', 'an_attribute')
        lay['/'].specify_group().attrs['__version__'] = h5tbx.__version__
        lay['devices'].specify_group('measurement_devices')

        with h5tbx.File() as h5:
            # this file should be having everything specified in the layout
            h5.create_dataset('velocity',
                              shape=(10, 20),
                              compression='gzip',
                              attrs={'units': 'm/s'})
            h5.attrs['comment'] = 'This is a valid comment'
            g = h5.create_group('devices/measurement_devices')
            h5['devices'].attrs['comment'] = 'This is a valid comment'
            h5['devices'].attrs['long_name'] = 'an_attribute'
            h5['devices/measurement_devices'].attrs['comment'] = 'This is a valid comment'
            h5.attrs['__version__'] = h5tbx.__version__

            res = lay.validate(h5)
            lay.report()
            self.assertEqual(lay.fails, 0)

            g.attrs['comment'] = '0 This is a valid comment'

            res = lay.validate(h5)
            self.assertEqual(lay.fails, 1)  # invalid comment
            # self.assertEqual(len(lay.get_succeeded_validations()), len(lay.called_validations) - 1)
            self.assertFalse(lay.is_validated)
            lay.print_failed_validations()
            lay.print_failed_validations(1)

    def test_dataset_validation(self):
        lay = Layout()
        # any dataset in root MUST have this attribute:
        lay['/'].specify_dataset(name=..., opt=False).attrs['standard_name'] = Equal('x_air_velocity')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)
            h5.attrs['standard_name'] = 'x_air_velocity'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)
            ds = h5.create_dataset('u', data=1)
            ds.attrs['standard_name'] = 'x_air_velocity'
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)
            ds = h5.create_dataset('v', data=1)
            ds.attrs['standard_name'] = 'y_air_velocity'
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

    def test_multiple_attributes(self):
        # one dataset must exist with x_pixel_coordinate.
        # this exact dataset must have the units 'pixel'
        lay = Layout()
        # g = lay['/'].specify_group(name=..., attrs={'a': 'aa',
        #                                            'b': 'bb'})
        g = lay['/'].specify_group(name=...)
        g.attrs = {'title': ..., 'user': ...}
        # g.specify_attrs(title=..., user=...)
        any_ds = lay['/'].specify_dataset(name=..., opt=False)
        any_ds.specify_attrs(dict(standard_name='x_pixel_coordinate', units='pixel'))

    def test_dataset_validation_2(self):
        lay = Layout()
        # ONLY ONE dataset in root MUST have this attribute:
        lay['/'].specify_dataset(name=...).specify_attrs(dict(standard_name=Equal('x_coordinate')), count=1)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            u = h5.create_dataset('u', data=1)
            u.attrs['standard_name'] = 'air_x_velocity'
            v = h5.create_dataset('v', data=1)
            v.attrs['standard_name'] = 'air_y_velocity'

            lay.validate(h5)

            self.assertEqual(lay.fails, 1)
            lay.print_failed_validations()

            x = h5.create_dataset('x', data=1)
            x.attrs['standard_name'] = 'x_coordinate'

            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_core4(self):
        lay = Layout()
        lay['devices'].specify_group('measurement_devices')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_group('devices/measurement_devices')
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_str(self):
        lay = Layout()
        lay['/'].specify_dataset(ndim=1)
        print(lay.subsequent_validations[0])

    def test_core2(self):
        lay = Layout()
        g = lay['group1']
        g.specify_dataset('dataset1', ndim=Equal(3))
        # d2 = lay['group1'] = Dataset('dataset2', ndim=In(1, 2, 3))

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)  # group1 is missing

            g = h5.create_group('group1')
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)  # group exists but dataset1 is missing

            g.create_dataset('dataset1', shape=(1, 2, 3))
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_wildcard(self):
        lay = Layout()
        lay['*'].attrs['long_name'] = 'group'
        lay['*'].specify_dataset(Any()).attrs['long_name'] = 'dataset'

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)
            lay.dumps()
            # h5.attrs['long_name'] = 'group'
            # ds = h5.create_dataset('ds', shape=(1, 2, 3))
            # # lay.validate(h5)
            # # self.assertEqual(lay.fails, 1)
            #
            # ds.attrs['long_name'] = 'dataset'
            # # lay.validate(h5)
            # # self.assertEqual(lay.fails, 0)
            #
            # ds2 = h5.create_dataset('a/ds2', shape=(1, 2, 3))
            # ds2.attrs['long_name'] = 'wrong'
            # lay.validate(h5)
            # self.assertEqual(lay.fails, 2)

    def test_core3(self):
        lay = Layout()
        lay['/'].attrs['version'] = h5tbx.__version__

        with h5tbx.File() as h5:
            h5.attrs['version'] = h5tbx.__version__
            lay.validate(h5)

        self.assertEqual(lay.fails, 0)
