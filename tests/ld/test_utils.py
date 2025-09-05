import unittest

from h5rdmtoolbox.ld.utils import _parse_obj_name


class TestUtile(unittest.TestCase):

    def test_parsing_obj_names(self):
        self.assertEqual(_parse_obj_name("/"), "/")
        self.assertEqual(_parse_obj_name(" "), "%20")
        self.assertEqual(_parse_obj_name("/My Group/"), "/My%20Group/")
        self.assertEqual(_parse_obj_name("/My Group/My Dataset"), "/My%20Group/My%20Dataset")
        self.assertEqual(_parse_obj_name("/My !&9]231,.0Group/My Dataset "), "/My%20%21%269%5D231%2C.0Group/My%20Dataset%20")
