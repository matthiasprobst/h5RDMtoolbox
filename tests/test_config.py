import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import CONFIG, config
from h5rdmtoolbox import H5File
from h5rdmtoolbox.wrapper import core, cflike


class TestConfg(unittest.TestCase):

    def test_setparameter(self):
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
