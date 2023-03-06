"""test h5rdmtolbox.conventions.cflike.units"""
import unittest
from pint.errors import UndefinedUnitError

import h5rdmtoolbox
from h5rdmtoolbox._config import ureg
from h5rdmtoolbox.conventions.cflike import units


class TestUnits(unittest.TestCase):
    """Test h5rdmtolbox.conventions.cflike.units"""

    def test_title(self):
        """Test title attribute"""
        h5rdmtoolbox.use('cflike')
        with h5rdmtoolbox.File() as h5:
            ds = h5.create_dataset('test', data=[1, 2, 3], units='m', long_name='test')
            with self.assertRaises(UndefinedUnitError):
                ds.units = 'test'
            with self.assertRaises(units.UnitsError):
                ds.units = ('test',)
            self.assertEqual(ds.units, 'm')
            # creat pint unit object:
            ds.units = ureg.mm
            self.assertEqual(ds.units, 'mm')
            del ds.units
            self.assertEqual(ds.units, None)
