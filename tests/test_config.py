import omegaconf
import unittest
from omegaconf.errors import ValidationError

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import CONFIG, config
from h5rdmtoolbox import H5File
from h5rdmtoolbox.wrapper import core


class TestConfig(unittest.TestCase):

    def test_config_type(self):
        self.assertIsInstance(h5tbx.config.CONFIG.xarray_unit_repr_in_plots, str)
        self.assertEqual(omegaconf.OmegaConf.get_type(h5tbx.config.CONFIG), h5tbx.config.H5tbxConfig)
        with self.assertRaises(AttributeError):
            h5tbx.config.CONFIG.does_not_exist
        with self.assertRaises(ValidationError):
            h5tbx.config.CONFIG.require_unit = 4.3
        with self.assertRaises(ValidationError):
            h5tbx.config.CONFIG.xarray_unit_repr_in_plots = 123
        h5tbx.config.CONFIG.xarray_unit_repr_in_plots = '('
        h5tbx.config.CONFIG.xarray_unit_repr_in_plots = '/'
        with self.assertRaises(ValidationError):
            h5tbx.config.CONFIG.ureg_format = 123

    def test_changing_ureg_format(self):
        self.assertEqual(h5tbx.config.CONFIG.ureg_format, 'C~')
        from h5rdmtoolbox.config import ureg
        q = ureg('1 mm')
        self.assertEqual(f'{q}', '1 mm')
        h5tbx.config.CONFIG.ureg_format = 'L~'
        self.assertEqual(f'{q}', r'\begin{pmatrix}1\end{pmatrix}\ \mathrm{mm}')


    def test_write_config(self):
        h5tbx.config.write_default_config()
        self.assertIsInstance(h5tbx.config.DEFAULT_CONFIG, omegaconf.DictConfig)
        self.assertEqual(h5tbx.config.DEFAULT_CONFIG['init_logger_level'], 'INFO')
        self.assertTrue(h5tbx.config.user_config_filename.exists())
        self.assertIsInstance(h5tbx.config.CONFIG, omegaconf.DictConfig)
        self.assertEqual(h5tbx.config.CONFIG['init_logger_level'], 'INFO')

    def test_setparameter(self):
        from h5rdmtoolbox.wrapper import cflike
        # config.set_config_parameter('convention', 'default')
        CONFIG['convention'] = 'default'
        self.assertEqual(CONFIG['convention'], 'default')
        self.assertEqual(config.CONFIG['convention'], 'default')
        h5tbx.use('default')

        with H5File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, core.H5File)
        h5.close()

        CONFIG['convention'] = 'cflike'
        self.assertEqual(CONFIG['convention'], 'cflike')
        self.assertEqual(config.CONFIG['convention'], 'cflike')
        h5tbx.use('cflike')

        self.assertEqual(config.CONFIG['convention'], 'cflike')
        with H5File() as h5:
            self.assertEqual(h5.__class__, cflike.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, cflike.H5File)
        h5.close()
