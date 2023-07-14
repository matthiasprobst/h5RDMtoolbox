"""Unit tests for h5rdmtoolbox.config"""
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox.wrapper import core


class TestConfig(unittest.TestCase):

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
        self.assertEqual(f'{q}', '\\SI[]{1}{\\milli\\meter}')
        h5tbx.set_config(ureg_format='C~')

    # def test_write_config(self):
    #     h5tbx.write_default_config()
    #     self.assertEqual(h5tbx.DEFAULT_CONFIG['init_logger_level'], 'ERROR')
    #     self.assertTrue(h5tbx.user_config_filename.exists())
    #     self.assertEqual(h5tbx.get_config('init_logger_level'), 'ERROR')

    def test_set_parameter(self):
        h5tbx.set_config(default_convention=None)
        self.assertEqual(h5tbx.get_config('default_convention'), None)
        h5tbx.use(None)

        with File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.File)

        h5 = File()
        self.assertEqual(h5.__class__, core.File)
        h5.close()

        h5tbx.set_config(default_convention='tbx')
        self.assertEqual(h5tbx.get_config('default_convention'), 'tbx')
        self.assertEqual(h5tbx.get_config('default_convention'), 'tbx')
        h5tbx.use('tbx')

        self.assertEqual(h5tbx.get_config('default_convention'), 'tbx')
        with File() as h5:
            self.assertEqual(h5.__class__, h5tbx.File)

        h5 = File()
        self.assertEqual(h5.__class__, h5tbx.File)
        h5.close()
