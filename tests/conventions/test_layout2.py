import unittest

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout2.core import Layout, Equal, GroupValidation, AttributeValidationManager, Regex, \
    Any


class TestLayout(unittest.TestCase):

    def test_core(self):
        # init layout:
        lay = Layout()

        # add gorups:
        g1 = lay.define_group('group1')  # lay.add_Group(Equal('group1'))
        g2 = lay[Equal('group2')]

        # check types:
        self.assertIsInstance(g1, GroupValidation)
        self.assertIsInstance(g2, GroupValidation)

        # # check __getitem__ method:
        # self.assertIsInstance(lay['group1'], GroupValidation)
        # self.assertIsInstance(lay['group2'], GroupValidation)

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
