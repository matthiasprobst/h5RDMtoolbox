"""Unit tests for h5rdmtoolbox.config"""
import omegaconf
import unittest
from omegaconf.errors import ValidationError

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import H5File
from h5rdmtoolbox import config
from h5rdmtoolbox.wrapper import core


class TestConfig(unittest.TestCase):

    def test_config_type(self):
        self.assertIsInstance(config.xarray_unit_repr_in_plots, str)
        self.assertEqual(omegaconf.OmegaConf.get_type(config), h5tbx._config.H5tbxConfig)
        with self.assertRaises(AttributeError):
            config.does_not_exist
        with self.assertRaises(ValidationError):
            config.require_unit = 4.3
        with self.assertRaises(ValidationError):
            config.xarray_unit_repr_in_plots = 123
        config.xarray_unit_repr_in_plots = '('
        config.xarray_unit_repr_in_plots = '/'
        with self.assertRaises(ValidationError):
            config.ureg_format = 123

    def test_changing_ureg_format(self):
        self.assertEqual(h5tbx.config.ureg_format, 'C~')
        from h5rdmtoolbox._config import ureg
        q = ureg('1 mm')
        self.assertEqual(f'{q}', '1 mm')
        config.ureg_format = 'L~'
        self.assertEqual(f'{q}', r'\begin{pmatrix}1\end{pmatrix}\ \mathrm{mm}')

    def test_write_config(self):
        h5tbx.write_default_config()
        self.assertIsInstance(h5tbx.DEFAULT_CONFIG, omegaconf.DictConfig)
        self.assertEqual(h5tbx.DEFAULT_CONFIG['init_logger_level'], 'INFO')
        self.assertTrue(h5tbx.user_config_filename.exists())
        self.assertIsInstance(config, omegaconf.DictConfig)
        self.assertEqual(config['init_logger_level'], 'INFO')

    def test_setparameter(self):
        from h5rdmtoolbox.wrapper import cflike
        # config.set_config_parameter('convention', 'default')
        config['default_convention'] = 'default'
        self.assertEqual(config['default_convention'], 'default')
        self.assertEqual(config['default_convention'], 'default')
        h5tbx.use('default')

        with H5File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, core.H5File)
        h5.close()

        config['default_convention'] = 'cflike'
        self.assertEqual(config['default_convention'], 'cflike')
        self.assertEqual(config['default_convention'], 'cflike')
        h5tbx.use('cflike')

        self.assertEqual(config['default_convention'], 'cflike')
        with H5File() as h5:
            self.assertEqual(h5.__class__, cflike.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, cflike.H5File)
        h5.close()
