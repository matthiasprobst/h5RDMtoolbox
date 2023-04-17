import unittest

import h5py

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout2.core import Layout, Equal, GroupValidation, AttributeValidationManager, Regex


class TestLayout(unittest.TestCase):

    def test_core(self):
        # init layout:
        lay = Layout()

        # add gorups:
        g1 = lay.add_group('group1')  # lay.add_Group(Equal('group1'))
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
            self.assertEqual(lay.fails, 2)
            g = h5.create_group('group1')
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
            g.attrs['test'] = '2'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
            g.attrs['long_name'] = '2'
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
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

    def test(self):
        lay = Layout()
        g = lay['group1']
        g.define_dataset('dataset1', ndim=Equal(3))
        # d2 = lay['group1'] = Dataset('dataset2', ndim=In(1, 2, 3))

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            g = h5.create_group('group1')
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

            g.create_dataset('dataset1', shape=(1, 2, 3))
            lay.validate(h5)
            self.assertEqual(lay.fails, 0)
