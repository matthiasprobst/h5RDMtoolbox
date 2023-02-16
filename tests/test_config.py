import omegaconf
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import CONFIG, config
from h5rdmtoolbox import H5File
from h5rdmtoolbox.wrapper import core


class TestConfig(unittest.TestCase):

    def test_write_config(self):
        h5tbx.config.write_default_config()
        self.assertIsInstance(h5tbx.config.DEFAULT_CONFIG, dict)
        self.assertEqual(h5tbx.config.DEFAULT_CONFIG['INIT_LOGGER_LEVEL'], 'INFO')
        self.assertTrue(h5tbx.config.user_config_filename.exists())
        self.assertIsInstance(h5tbx.config.CONFIG, omegaconf.DictConfig)
        self.assertEqual(h5tbx.config.CONFIG['INIT_LOGGER_LEVEL'], 'INFO')

    def test_setparameter(self):
        from h5rdmtoolbox.wrapper import cflike
        # config.set_config_parameter('CONVENTION', 'default')
        CONFIG['CONVENTION'] = 'default'
        self.assertEqual(CONFIG['CONVENTION'], 'default')
        self.assertEqual(config.CONFIG['CONVENTION'], 'default')
        h5tbx.use('default')

        with H5File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, core.H5File)
        h5.close()

        CONFIG['CONVENTION'] = 'cflike'
        self.assertEqual(CONFIG['CONVENTION'], 'cflike')
        self.assertEqual(config.CONFIG['CONVENTION'], 'cflike')
        config.set_config_parameter('CONVENTION', 'cflike')
        h5tbx.use('cflike')

        self.assertEqual(config.CONFIG['CONVENTION'], 'cflike')
        with H5File() as h5:
            self.assertEqual(h5.__class__, cflike.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, cflike.H5File)
        h5.close()
