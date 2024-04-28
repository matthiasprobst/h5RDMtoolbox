"""Testing the standard attributes"""
import datetime
import pathlib
import pint
import pydantic
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

    def test_version(self):
        class Version(BaseModel):
            ver: toolbox_validators.versionType

        with self.assertRaises(TypeError):
            Version(ver=3.4)

        with self.assertRaises(ValidationError):
            Version(ver='invalid')

        vers = Version(ver='1.0.0')
        self.assertEqual('1.0.0', vers.ver)
        vers = Version(ver='1.0.0-alpha')
        self.assertEqual('1.0.0-alpha', vers.ver)

    def test_validate_regex(self):
        from h5rdmtoolbox.convention.generate import RegexProcessor

        rp = RegexProcessor({r'validator': r'regex("^[a-zA-Z0-9_]*$")'})
        self.assertEqual(r'"^[a-zA-Z0-9_]*$"', rp.re_pattern)

        rp = RegexProcessor({r'validator': r'$regex(^[a-zA-Z].*(?<!\s)$)'})
        self.assertEqual(r'^[a-zA-Z].*(?<!\s)$', rp.re_pattern)

    def test_validate_identifier(self):
        class Identifier(BaseModel):
            identifier: toolbox_validators.identifierType

        with self.assertRaises(ValueError):
            Identifier(orcid=3.4)
        with self.assertRaises(TypeError):
            Identifier(identifier=3.4)
        with self.assertRaises(pydantic.ValidationError):
            Identifier(identifier='0000-0001-8729-0482')
        Identifier(identifier='https://orcid.org/0000-0002-1825-0097')
        with self.assertRaises(pydantic.ValidationError):
            Identifier(identifier='https://orcid.org/0000-0002-1825-0096')  # invalid orcid due to checksum

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

        with self.assertRaises(ValueError):
            Validator(quantity='3.4 kilo meter')

    def test_validate_units(self):
        class Validator(BaseModel):
            units: toolbox_validators.unitsType

        Validator(units=pint.Unit('m'))
        self.assertIsInstance(Validator(units=pint.Unit('m')).units, pint.Unit)
        self.assertIsInstance(Validator(units='m').units, pint.Unit)

        with self.assertRaises(pydantic.ValidationError):
            Validator(units={'unit': 'm'})

    def test_date_format(self):
        class Validator(BaseModel):
            date: toolbox_validators.dateFormatType

        self.assertIsInstance(Validator(date='2021-01-01').date,
                              datetime.datetime)

        with self.assertRaises(TypeError):
            Validator(date=3.4)
