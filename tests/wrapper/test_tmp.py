import logging
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.tutorial import get_standard_name_table
from h5rdmtoolbox.wrapper import set_loglevel

logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')


class TestTmp(unittest.TestCase):

    def setUp(self):
        yaml_filename = h5tbx.tutorial.get_standard_attribute_yaml_filename()
        cv = h5tbx.conventions.Convention.from_yaml(yaml_filename, 'tutorial-convention')
        cv.register()
        h5tbx.use('tutorial-convention')

    def test_tmp(self):
        h5tbx.use('tutorial-convention')
        with h5tbx.File(standard_name_table=get_standard_name_table(),
                        contact='https://orcid.org/0000-0001-8729-0482') as h5:
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
