"""Unit tests for h5rdmtoolbox.config"""
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox.wrapper import core


class TestConfig(unittest.TestCase):

    def test_set_logger(self):
        with h5tbx.set_config(init_logger_level='DEBUG'):
            self.assertEqual(h5tbx.get_config()['init_logger_level'], 'DEBUG')
        with h5tbx.set_config(init_logger_level=10):
            self.assertEqual(h5tbx.get_config()['init_logger_level'], 10)
        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level='invalid'):
                pass
        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level=100):
                pass

        with self.assertRaises(KeyError):
            with h5tbx.set_config(invalid='invalid'):
                pass

        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level=3.4):
                pass

    def test_config_type(self):
        self.assertIsInstance(h5tbx.get_config('xarray_unit_repr_in_plots'), str)
        with self.assertRaises(KeyError):
            h5tbx.get_config('does_not_exist')
        with self.assertRaises(ValueError):
            h5tbx.set_config(require_unit=4.3)
        with self.assertRaises(ValueError):
            h5tbx.set_config(xarray_unit_repr_in_plots=123)
        h5tbx.set_config(xarray_unit_repr_in_plots='(')
        h5tbx.set_config(xarray_unit_repr_in_plots='/')
        with self.assertRaises(ValueError):
            h5tbx.set_config(ureg_format=123)

    def test_changing_ureg_format(self):
        self.assertEqual(h5tbx.get_config('ureg_format'), 'C~')
        ureg = h5tbx.get_ureg()
        self.assertEqual(h5tbx.get_ureg().default_format, h5tbx.get_config('ureg_format'))
        q = ureg('1 mm')
        self.assertEqual(f'{q}', '1 mm')
        h5tbx.set_config(ureg_format='Lx~')
        self.assertEqual(h5tbx.get_config('ureg_format'), 'Lx~')
        self.assertEqual(f'{q}', '\\SI[]{\\begin{pmatrix}1\\end{pmatrix}}{\\milli\\meter}')
        h5tbx.set_config(ureg_format='C~')
        self.assertEqual(f'{q}', '1 mm')

    def test_set_parameter(self):
        h5tbx.use(None)

        with File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.File)

        h5 = File()
        self.assertEqual(h5.__class__, core.File)
        h5.close()

        h5tbx.use('h5tbx')

        with File() as h5:
            self.assertEqual(h5.__class__, h5tbx.File)

        h5 = File()
        self.assertEqual(h5.__class__, h5tbx.File)
        h5.close()
