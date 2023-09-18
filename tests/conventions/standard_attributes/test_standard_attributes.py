"""Testing the standard attributes"""
import pint
import unittest
from typing import Union

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions.standard_attributes import StandardAttribute


class TestStandardAttributes(unittest.TestCase):

    @staticmethod
    def assertPintUnitEqual(unit1: [str, pint.Unit], unit2: Union[str, pint.Unit]):
        """Assert that two units are equal by converting them to pint.Unit"""
        assert pint.Unit(unit1) == pint.Unit(unit2)

    def setUp(self) -> None:
        self.connected = h5tbx.utils.has_internet_connection()

    def assert_standard_attribute(self, sa):
        self.assertIsInstance(sa.name, str)
        self.assertIsInstance(sa.description, str)
        self.assertIsInstance(sa.is_positional(), bool)
        self.assertIsInstance(sa.target_method, str)

    def test_standard_attribute_basics(self):
        with self.assertRaises(TypeError):
            test = StandardAttribute('test',
                                     validator={'$type': 'string'},
                                     target_method='create_dataset',
                                     description='A test',
                                     )
