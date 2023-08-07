import unittest
from datetime import datetime

from h5rdmtoolbox.conventions.standard_attributes.validators import core
from h5rdmtoolbox.conventions.standard_attributes.validators.core import _eval_type


class TestValidators(unittest.TestCase):

    def test_eval_type(self):
        self.assertEqual(_eval_type('int'), int)
        self.assertEqual(_eval_type('$int'), int)
        self.assertEqual(_eval_type('float'), float)
        self.assertEqual(_eval_type('$float'), float)
        self.assertEqual(_eval_type('$list'), list)
        with self.assertRaises(KeyError):
            _eval_type('bla')

    def test_eval_validators(self):
        n = core.NoneValidator()
        self.assertEqual(n(13.4, None), 13.4)

        dt = core.DateTimeValidator()
        now = datetime.now().isoformat()
        self.assertEqual(dt(now, None), now)
        self.assertEqual('2020-01-01T12:00:00', dt('2020-01-01T12:00:00', None))
        with self.assertRaises(ValueError):
            dt(3.4, None)
