import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper import core, h5ext


class TestH5Ext(unittest.TestCase):

    def test_h5ext(self):
        h5tbx.use('h5py')
        with core.File() as h51:
            h51.create_dataset('ds', data=1)
        with core.File() as h52:
            h52.create_external_link('ds', h51.hdf_filename, '/ds')
            self.assertIsInstance(h52['ds'], core.Dataset)
            with self.assertRaises(ValueError):
                h52.create_external_link('ds', h51.hdf_filename, '/ds')
            h52.create_external_link('ds', h51.hdf_filename, '/ds', overwrite=True)
            self.assertIsInstance(h52['ds'], core.Dataset)

        with h5ext.ExternalLink(h52.hdf_filename, 'ds') as ext_ds:
            self.assertIsInstance(ext_ds, core.Dataset)
