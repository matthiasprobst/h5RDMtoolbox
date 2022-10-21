import unittest

from h5rdmtoolbox import H5File
from h5rdmtoolbox import config
from h5rdmtoolbox.wrapper import core, cflike


class TestConfg(unittest.TestCase):

    def test_setparameter(self):
        config.set_config_parameter('CONVENTION', 'default')
        self.assertEqual(config.CONFIG['CONVENTION'], 'default')
        with H5File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, core.H5File)
        h5.close()

        config.set_config_parameter('CONVENTION', 'cflike')
        self.assertEqual(config.CONFIG['CONVENTION'], 'cflike')
        with H5File() as h5:
            self.assertEqual(h5.__class__, cflike.H5File)

        h5 = H5File()
        self.assertEqual(h5.__class__, cflike.H5File)
        h5.close()
