import unittest

import h5py

from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout2.core import Layout, Equal, GroupValidation, AttributeValidationManager, Any


class TestLayout(unittest.TestCase):

    def test_core(self):
        # init layout:
        lay = Layout()

        # add gorups:
        g1 = lay.add_group('group1')  # lay.add_Group(Equal('group1'))
        g2 = lay.add_group(Equal('group2'))

        # check types:
        self.assertIsInstance(g1, GroupValidation)
        self.assertIsInstance(g2, GroupValidation)

        # # check __getitem__ method:
        # self.assertIsInstance(lay['group1'], GroupValidation)
        # self.assertIsInstance(lay['group2'], GroupValidation)

        self.assertIsInstance(g1.attrs, AttributeValidationManager)
        g1.attrs.add(Equal('attr1'), Any())

        print(lay)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
            g = h5.create_group('group1')
            lay.validate(h5)
            self.assertEqual(lay.fails, 2)
            g.attrs['attr1'] = 1
            lay.validate(h5)
            self.assertEqual(lay.fails, 1)

        # a11 = g1.attrs['attr1'] = Any()
