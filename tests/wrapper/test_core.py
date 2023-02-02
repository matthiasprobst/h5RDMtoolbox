import logging
import pandas as pd
import unittest
from pint_xarray import unit_registry as ureg

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.config import CONFIG
from h5rdmtoolbox.wrapper import set_loglevel

logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')

ureg.default_format = CONFIG.UREG_FORMAT

h5tbx.use('default')


class TestCore(unittest.TestCase):

    def test_from_csv(self):
        df = pd.DataFrame({'x': [1, 5, 10], 'y': [-3, 20, 0]})
        csv_filename = h5tbx.utils.generate_temporary_filename(suffix='.csv')
        df.to_csv(csv_filename)
        with h5tbx.H5File() as h5:
            h5.create_datasets_from_csv(csv_filename=csv_filename)
