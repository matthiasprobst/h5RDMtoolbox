import logging
import unittest
from pint_xarray import unit_registry as ureg

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import config
from h5rdmtoolbox import use
from h5rdmtoolbox.wrapper import set_loglevel

use('cflike')
logger = logging.getLogger('h5rdmtoolbox.wrapper')
set_loglevel('ERROR')

ureg.default_format = config.CONFIG.UREG_FORMAT


class TestFind(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        with h5tbx.H5File() as h5:
            h5.attrs['project'] = 'tutorial'
            h5.create_dataset('velocity', data=[1, 2, -1], units='m/s', standard_name='x_velocity')
            g = h5.create_group('sub')
            g.create_dataset('velocity', data=[4, 0, -3, 12, 3], units='m/s', standard_name='x_velocity')
            h5.dump()
            self.filename = h5.hdf_filename

    def test_find_rec_False(self):
        with h5tbx.H5File(self.filename) as h5:
            print('\nfind basename=velocity in sub/:')
            self.assertEqual(h5['sub'].find({'$basename': 'velocity'}, '$dataset', rec=False)[0],
                             h5['sub/velocity'])

            self.assertEqual(len(h5.find({'$basename': {'$regex': 'sub'}}, '$group', rec=False)), 1)
            self.assertEqual(h5.find({'$basename': {'$regex': 'sub'}}, '$group', rec=False)[0], h5['sub'])
            self.assertEqual(h5.find_one({'$basename': {'$regex': 'sub'}}, '$group', rec=False), h5['sub'])
            self.assertEqual(len(h5.find({'$basename': {'$regex': 'sub'}}, '$group', rec=True)), 1)
            self.assertEqual(h5.find({'$basename': {'$regex': 'sub'}}, '$group', rec=True)[0], h5['sub'])
            self.assertEqual(h5.find_one({'$basename': {'$regex': 'sub'}}, '$group', rec=True), h5['sub'])
