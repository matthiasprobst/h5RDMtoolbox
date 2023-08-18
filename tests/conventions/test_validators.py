import unittest
from datetime import datetime

from h5rdmtoolbox.conventions import validator


class TestValidators(unittest.TestCase):

    def test_eval_type(self):
        self.assertEqual(validator._eval_type('int'), int)
        self.assertEqual(validator._eval_type('$int'), int)
        self.assertEqual(validator._eval_type('float'), float)
        self.assertEqual(validator._eval_type('$float'), float)
        self.assertEqual(validator._eval_type('$list'), list)
        with self.assertRaises(KeyError):
            validator._eval_type('bla')

    def test_eval_validators(self):
        n = validator.NoneValidator()
        self.assertEqual(n(13.4, None), 13.4)

        dt = validator.DateTimeValidator()
        now = datetime.now().isoformat()
        self.assertEqual(dt(now, None), now)
        self.assertEqual('2020-01-01T12:00:00', dt('2020-01-01T12:00:00', None))
        with self.assertRaises(ValueError):
            dt(3.4, None)
