"""Testing the standard attributes"""
import datetime
import pathlib
import pint
import unittest
from pydantic import BaseModel
from pydantic import ValidationError
from typing import List, Union

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention import toolbox_validators

__this_dir__ = pathlib.Path(__file__).parent


class TestTbxValidators(unittest.TestCase):

    def test_validate_list_of_str(self):
        class MyStr(BaseModel):
            los: Union[str, List[str]]

        with self.assertRaises(ValidationError):
            MyStr(los=3.4)

        MyStr(los='3.4')

        MyStr(los=['3.4', 'str'])

        with self.assertRaises(ValidationError):
            MyStr(los=['3.4', 3.4])

        cv = h5tbx.convention.from_yaml(__this_dir__ / 'ListOfStr.yaml', overwrite=True)
        with h5tbx.use(cv):
            print(cv)
            with h5tbx.File(keywords=['1', '2']) as h5:
                self.assertListEqual(['1', '2'], h5.keywords)
        cv.delete()

    def test_validate_regex(self):
        from h5rdmtoolbox.convention.generate_utils import RegexProcessor

        rp = RegexProcessor({'validator': 'regex(r"^[a-zA-Z0-9_]*$")'})
        self.assertEqual('r"^[a-zA-Z0-9_]*$"', rp.re_pattern)

        rp = RegexProcessor({'validator': '$regex(^[a-zA-Z].*(?<!\s)$)'})
        self.assertEqual('^[a-zA-Z].*(?<!\s)$', rp.re_pattern)

    def test_validate_orcid(self):
        class Validator(BaseModel):
            orcid: toolbox_validators.orcidType

        with self.assertRaises(TypeError):
            Validator(orcid=3.4)
        Validator(orcid=h5tbx.__author_orcid__)
        Validator(orcid='0000-0001-8729-0482')
        with self.assertRaises(ValueError):
            Validator(orcid='0000-0001-8729-XXXX')

    def test_validate_url(self):
        class Validator(BaseModel):
            url: toolbox_validators.validators["url"]

        with self.assertRaises(TypeError):
            Validator(url=3.4)
        Validator(url='https://github.com/matthiasprobst/h5RDMtoolbox')
        Validator(url=['https://github.com/matthiasprobst/h5RDMtoolbox', ])
        Validator(url=['https://github.com/matthiasprobst/h5RDMtoolbox',
                       'https://www.github.com'])
        with self.assertRaises(ValueError):
            Validator(url=['https://github.com/matthiasprobst/h5RDMtoolbox',
                           'https://www.github.com',
                           'this.does.not.work.for.sure'])

        with self.assertRaises(TypeError):
            Validator(url={'url1': 'https://github.com/matthiasprobst/h5RDMtoolbox'})

    def test_validate_quantity(self):
        class Validator(BaseModel):
            quantity: toolbox_validators.quantityType

        Validator(quantity=pint.Quantity(3.4, 'm'))
        self.assertIsInstance(Validator(quantity=pint.Quantity(3.4, 'm')).quantity, pint.Quantity)
        self.assertIsInstance(Validator(quantity='3.3 m').quantity, pint.Quantity)
        self.assertEqual(Validator(quantity='3.3 m').quantity.magnitude, 3.3)

    def test_validate_units(self):
        class Validator(BaseModel):
            units: toolbox_validators.unitsType

        Validator(units=pint.Unit('m'))
        self.assertIsInstance(Validator(units=pint.Unit('m')).units, pint.Unit)
        self.assertIsInstance(Validator(units='m').units, pint.Unit)

    def test_date_format(self):
        class Validator(BaseModel):
            date: toolbox_validators.dateFormatType

        self.assertIsInstance(Validator(date='2021-01-01').date,
                              datetime.datetime)
        with self.assertRaises(TypeError):
            Validator(date=3.4)
