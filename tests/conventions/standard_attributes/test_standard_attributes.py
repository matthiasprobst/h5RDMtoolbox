"""Testing the standard attributes"""
import pint
import unittest
from typing import Union

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention.consts import DefaultValue
from h5rdmtoolbox.convention.standard_attributes import StandardAttribute


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
            StandardAttribute('test',
                              validator={'$type': 'string'},
                              target_method=3.4,
                              description='A test',
                              )

        with self.assertRaises(ValueError):
            StandardAttribute('test',
                              validator={'$type': 'string'},
                              target_method='create_dataset2',
                              description='A test',
                              )

        test = StandardAttribute('test',
                                 validator={'$type': 'string'},
                                 target_method='create_dataset',
                                 description='A test',
                                 default_value='none'
                                 )
        self.assertEqual(test.default_value, None)

        test = StandardAttribute('test',
                                 validator={'$type': 'string'},
                                 target_method='create_dataset',
                                 description='A test',
                                 alternative_standard_attribute='alternative',
                                 default_value='$empty'
                                 )
        self.assertEqual(test.default_value, DefaultValue.EMPTY)
        self.assertEqual(test.alternative_standard_attribute, 'alternative')

        self.assertFalse(test.is_obligatory())
