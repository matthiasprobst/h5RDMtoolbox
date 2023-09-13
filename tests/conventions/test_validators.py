import unittest
from datetime import datetime

from h5rdmtoolbox.conventions import validators


class TestValidators(unittest.TestCase):

    def test_eval_type(self):
        self.assertEqual(validators._eval_type('int'), int)
        self.assertEqual(validators._eval_type('$int'), int)
        self.assertEqual(validators._eval_type('float'), float)
        self.assertEqual(validators._eval_type('$float'), float)
        self.assertEqual(validators._eval_type('$list'), list)
        with self.assertRaises(KeyError):
            validators._eval_type('bla')

    def test_eval_validators(self):
        n = validators.NoneValidator()
        self.assertEqual(n(13.4, None), 13.4)

        dt = validators.DateTimeValidator()
        now = datetime.now().isoformat()
        self.assertEqual(dt(now, None), now)
        self.assertEqual('2020-01-01T12:00:00', dt('2020-01-01T12:00:00', None))
        with self.assertRaises(ValueError):
            dt(3.4, None)

    def test_symbol_validator(self):
        s = validators.SymbolValidator()
        self.assertEqual(s('bla', None), 'bla')
        with self.assertRaises(ValueError):
            s(3.4, None)
