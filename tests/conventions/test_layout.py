import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout import *


class TestLayout(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

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
            self.assertTrue(lay.is_validated)

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

        i = In(1, 2, 3)
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

    def test_core(self):
        # init layout:
        lay = Layout()

        # add groups, which MUST exist:
        g1 = lay.define_group('group1')  # lay.add_Group(Equal('group1'))
        g2 = lay[Equal('group2')]

        # check types:
        self.assertIsInstance(g1, GroupValidation)
        self.assertIsInstance(g2, GroupValidation)

        self.assertIsInstance(g1.attrs, AttributeValidationManager)
        # g1.attrs.add(Equal('attr1'), Any())

        # add an attribute to group1, which MUST exist:
        g1.attrs.add('long_name', 'an_attribute')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # both groups are missing

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
        self.assertEqual(lay.fails, 2)

        print(lay)

    def test_docs_example(self):
        lay = Layout()

        dv = lay['*'].define_dataset(compression='gzip')
        lay['*'].define_dataset().attrs['units'] = ...
        lay['*'].define_group().attrs['comment'] = Regex(r'^[^ 0-9].*')

        lay['devices'].attrs.add('long_name', 'an_attribute')
        lay['/'].define_group().attrs['__version__'] = h5tbx.__version__
        lay['devices'].define_group('measurement_devices')

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
            self.assertEqual(len(lay.get_succeeded_validations()), len(lay.called_validations) - 1)
            self.assertFalse(lay.is_validated)
            lay.print_failed_validations()
            lay.print_failed_validations(1)

    def test_core4(self):
        lay = Layout()
        lay['devices'].define_group('measurement_devices')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_group('devices/measurement_devices')
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)

    def test_str(self):
        lay = Layout()
        lay['/'].define_dataset(ndim=1)
        print(lay.children[0])

    def test_core2(self):
        lay = Layout()
        g = lay['group1']
        g.define_dataset('dataset1', ndim=Equal(3))
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
        lay['*'].define_dataset(Any()).attrs['long_name'] = 'dataset'

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
