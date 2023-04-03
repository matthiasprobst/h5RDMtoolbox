import logging
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.tutorial import get_standard_name_table
from h5rdmtoolbox.wrapper import set_loglevel

logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')


class TestTmp(unittest.TestCase):

    def setUp(self):
        h5tbx.use('tbx')

    def test_tmp(self):
        h5tbx.use('tbx')
        with h5tbx.File(standard_name_table=get_standard_name_table()) as h5:
            h5.create_dataset(name='test', shape=(1, 2), units='m/s', standard_name='x_velocity')
            h5.sdump()

        # now standard_name_table should not be an expected argument:
        h5tbx.use(None)
        with self.assertRaises(TypeError):
            with h5tbx.File(standard_name_table=get_standard_name_table()):
                pass

        with h5tbx.File() as h5:  # issue here: undo the function argument thing...
            with self.assertRaises(TypeError):
                h5.create_dataset(name='test', shape=(1, 2), units='m/s', standard_name='x_velocity')

        with h5tbx.File() as h5:
            h5.create_dataset(name='test', shape=(1, 2))
