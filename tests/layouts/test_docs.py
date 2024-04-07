"""Testing the example used in the documentation."""

"""Test the mongoDB interface"""
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import layout
from h5rdmtoolbox.database import hdfdb


class TestDocExample(unittest.TestCase):

    def test_doc_example(self):
        with h5tbx.File() as h5:
            h5.create_dataset('u', shape=(3, 5), compression='lzf')
            h5.create_dataset('v', shape=(3, 5), compression='gzip')
            h5.create_group('instruments', attrs={'description': 'Instrument data'})

        lay = layout.Layout()

        # the file must have datasets (this spec makes more sense with the following spec)
        spec_all_dataset = lay.add(
            hdfdb.FileDB.find,  # query function
            flt={},
            objfilter='dataset',
            n={'$gte': 1},  # at least one dataset must exist
            description='At least one dataset exists'
        )

        # all datasets must be compressed with gzip (conditional spec. only called if parent spec is successful)
        spec_compression = spec_all_dataset.add(
            hdfdb.FileDB.find,  # query function
            flt={'$compression': 'gzip'},  # query parameter
            n=1,
            description='Compression of any dataset is "gzip"'
        )

        # the file must have the dataset "/u"
        spec_ds_u = lay.add(
            hdfdb.FileDB.find,  # query function
            flt={'$name': '/u'},
            objfilter='dataset',
            n=1,
            description='Dataset "/u" exists'
        )

        # we added one specification to the layout:
        lay.specifications

        res = lay.validate(h5.hdf_filename)
        res.print_summary()

        self.assertEqual(spec_compression.n_calls, 2)
        self.assertFalse(lay.is_valid())


        with h5tbx.File() as h5:
            h5.create_dataset('u', shape=(3, 5), compression='gzip')
            h5.create_dataset('v', shape=(3, 5), compression='gzip')
            h5.create_group('instruments', attrs={'description': 'Instrument data'})

            res = lay.validate(h5)

        self.assertEqual(spec_compression.n_calls, 2)
        res.print_summary()
        self.assertTrue(lay.is_valid())
