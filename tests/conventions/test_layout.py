import unittest

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout import Layout, Equal, GroupValidation, AttributeValidationManager, Regex, \
    Any


class TestLayout(unittest.TestCase):

    def test_core(self):
        # init layout:
        lay = Layout()

        # add groups:
        g1 = lay.define_group('group1')  # lay.add_Group(Equal('group1'))
        g2 = lay[Equal('group2')]

        # check types:
        self.assertIsInstance(g1, GroupValidation)
        self.assertIsInstance(g2, GroupValidation)

        self.assertIsInstance(g1.attrs, AttributeValidationManager)
        # g1.attrs.add(Equal('attr1'), Any())
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
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

            print(lay)

    def test_docs_example(self):
        lay = Layout()

        # dv = lay['*'].define_dataset(compression='gzip')
        # lay['*'].define_dataset().attrs['units'] = ...
        lay['*'].define_group().attrs['comment'] = Regex(r'^[^ 0-9].*')

        lay['devices'].attrs.add('long_name', 'an_attribute')
        # lay['/'].define_group().attrs['__version__'] = h5tbx.__version__
        # lay['devices'].define_group('measurement_devices')

        with h5tbx.File() as h5:
            # h5.create_dataset('velocity',
            #                   shape=(10, 20),
            #                   compression='gzip',
            #                   attrs={'units': 'm/s'})
            g = h5.create_group('devices/measurement_devices')
            g.attrs['comment'] = 'This is a valid comment'
            # h5.create_group('devices/measurement_devices')

            res = lay.validate(h5)
            self.assertEqual(lay.fails, 3)  # root and device has no comment

            h5.attrs['comment'] = 'This is a valid comment'
            res = lay.validate(h5)
            self.assertEqual(lay.fails, 2)  # device has no comment

            g.attrs['comment'] = ' 0 this is not a valid comment'
            res = lay.validate(h5)
            self.assertEqual(lay.fails, 3)  # device has no comment

            h5['devices'].attrs['long_name'] = 'an_attribute'

            lay.validate(h5)
            self.assertEqual(lay.fails, 2)

    def test_core4(self):
        lay = Layout()
        lay['devices'].define_group('measurement_devices')

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_group('devices/measurement_devices')
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)
            print(lay.print_failed())

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
