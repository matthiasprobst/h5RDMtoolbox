import unittest

from h5rdmtoolbox.wrapper import core, h5ext


class TestH5Ext(unittest.TestCase):

    def test_h5ext(self):
        with core.H5File() as h51:
            h51.create_dataset('ds', data=1)
        with core.H5File() as h52:
            h52.create_external_link('ds', h51.hdf_filename, '/ds')
            self.assertIsInstance(h52['ds'], core.H5Dataset)

        with h5ext.ExternalLink(h52.hdf_filename, 'ds') as ext_ds:
            self.assertIsInstance(ext_ds, core.H5Dataset)
