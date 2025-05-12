import json
import pathlib
import unittest

import pint
import yaml

from h5rdmtoolbox.convention import utils
from h5rdmtoolbox.utils import generate_temporary_filename


class TestTranslation(unittest.TestCase):

    def test_yaml2json(self):
        data = {
            "__name__": "tutorial-units-convention",
            "__institution__": "https://orcid.org/members/001G000001e5aUTIAY",
            "__contact__": "https://orcid.org/0000-0001-8729-0482",
            "units": {
                "target_method": "create_dataset",
                "validator": "$units",
                "description": "The physical unit of the dataset. If dimensionless, the unit is ''.",
                "default_value": "$EMPTY"
            }
        }
        yaml_filename = generate_temporary_filename(suffix='.yaml')
        with open(yaml_filename, 'w') as f:
            yaml.safe_dump(data, f)

        json_filename = utils.yaml2json(yaml_filename)
        self.assertEqual(json_filename.suffix, '.json')
        self.assertEqual(json_filename.stem, yaml_filename.stem)
        with open(json_filename, 'r') as f:
            output = json.load(f)
        self.assertDictEqual(data, output)

        json_filename = utils.yaml2json(yaml_filename,
                                        json_filename=yaml_filename.parent / 'test.json')
        self.assertIsInstance(json_filename, pathlib.Path)
        self.assertEqual(json_filename.absolute(),
                         yaml_filename.parent / 'test.json')
        json_filename.unlink(missing_ok=True)

    def test_json2yaml(self):
        data = {
            "__name__": "tutorial-units-convention",
            "__institution__": "https://orcid.org/members/001G000001e5aUTIAY",
            "__contact__": "https://orcid.org/0000-0001-8729-0482",
            "units": {
                "target_method": "create_dataset",
                "validator": "$units",
                "description": "The physical unit of the dataset. If dimensionless, the unit is ''.",
                "default_value": "$EMPTY"
            }
        }
        json_filename = generate_temporary_filename(suffix='.json')
        with open(json_filename, 'w') as f:
            json.dump(data, f)

        yaml_filename = utils.json2yaml(json_filename)
        self.assertEqual(yaml_filename.suffix, '.yaml')
        self.assertEqual(yaml_filename.stem, json_filename.stem)
        with open(yaml_filename, 'r') as f:
            output = yaml.safe_load(f)
        self.assertDictEqual(data, output)

        yaml_filename = utils.json2yaml(json_filename,
                                        yaml_filename=json_filename.parent / 'test.yaml')
        self.assertIsInstance(yaml_filename, pathlib.Path)
        self.assertEqual(yaml_filename.absolute(),
                         json_filename.parent / 'test.yaml')

    def test_equal_base_units(self):
        u1 = pint.Unit('m')
        u2 = pint.Unit('km')
        u3 = pint.Unit('m/s')
        self.assertTrue(utils.equal_base_units(u1, u1))
        self.assertTrue(utils.equal_base_units(u1, u2))
        self.assertFalse(utils.equal_base_units(u1, u3))

    def test_is_valid_email_address(self):
        self.assertTrue(utils.is_valid_email_address('hallo@gmail.com'))
        self.assertFalse(utils.is_valid_email_address('hallo@gmail'))
        self.assertFalse(utils.is_valid_email_address('hallo.de'))

    def test_check_url(self):
        with self.assertWarns(UserWarning):
            utils.check_url('www.no-google.de', raise_error=False, print_warning=True)
        with self.assertWarns(UserWarning):
            utils.check_url('https://www.no-google.de', raise_error=False, print_warning=True)
        with self.assertRaises(Exception):
            utils.check_url('https://www.no-google.de', raise_error=True, print_warning=False)
        with self.assertRaises(ValueError):
            utils.check_url('https://www.no-google.de', raise_error=True, print_warning=True)
