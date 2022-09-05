import unittest

import pandas as pd

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.h5database import H5Files
from h5rdmtoolbox.h5database.files import H5Objects


class TestH5Files(unittest.TestCase):

    def test_H5Files(self):
        fnames = []
        with h5tbx.H5File() as h51:
            h51.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

            with h5tbx.H5File() as h52:
                h52.create_dataset('ds', shape=(1, 2, 3), units='', long_name='long name 2')
                fnames.append(h52.filename)

                with H5Files(fnames) as h5s:
                    res = h5s.find({'$dataset': {'$basename': 'ds'}})
                    self.assertEqual([h51.ds, h52.ds], res)
                    self.assertEqual(res[0].long_name[-1], '1')
                    self.assertEqual(res[1].long_name[-1], '2')
                    res = h5s.find_one({'$dataset': {'$basename': 'ds'}})
                    self.assertEqual(h51.ds, res)

    def test_getitem(self):
        fnames = []
        with h5tbx.H5File() as h51:
            h51.create_dataset('ds', data=(1, 2, 3), units='', long_name='long name 1')
            fnames.append(h51.filename)

        with h5tbx.H5File() as h52:
            h52.create_dataset('ds', data=(4, 5, 6), units='', long_name='long name 2')
            fnames.append(h52.filename)

        with H5Files(fnames) as h5s:
            self.assertIsInstance(h5s['ds'], H5Objects)
            df1 = pd.DataFrame({'ds': (1, 2, 3)})
            df2 = pd.DataFrame({'ds': (4, 5, 6)})
            concat0 = pd.concat([df1, df2], names=['item', ], axis=0, join='inner', keys=['tmp0', 'tmp1'])

            print(h5s['ds'][:].to_DataFrame(axis=0, join='inner'))
            self.assertEqual(concat0, h5s['ds'][:].to_DataFrame(axis=0, join='inner'))
            print(h5s['ds'][:].to_DataFrame(axis=1, join='inner'))
            # concat1 = pd.concat([df1, df2], names=['item', 'item'], axis=1, join='inner', keys=['tmp0', 'tmp1'])
            # self.assertEqual(concat1, h5s['ds'][:].to_DataFrame(axis=1, join='inner'))
