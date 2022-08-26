import unittest
from pprint import pprint

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.conventions import translations


class TestTranslation(unittest.TestCase):

    def test_read_yml(self):
        self.assertIsInstance(translations.from_yaml('../../conventions/snt_pivview.yml'), dict)
        pprint(translations.from_yaml('../../conventions/snt_pivview.yml'))

    def test_translation(self):
        with h5tbx.H5File() as h5:
            h5.create_dataset('ds', shape=(2,), units='', long_name='long name')
            h5.create_dataset('ds2', shape=(2,), units='', long_name='long name')
            h5.create_dataset('ds3', shape=(2,), units='', long_name='long name')
            h5.create_dataset('root/ds', shape=(2,), units='', long_name='long name')
            h5.create_dataset('root/ds2', shape=(2,), units='', long_name='long name')
            h5.create_dataset('root/ds3', shape=(2,), units='', long_name='long name')

            for k in ('ds', 'ds2', 'ds3', '/root/ds', '/root/ds2', '/root/ds3'):
                self.assertNotIn('standard_name', h5[k].attrs)

            snt = {'/root/ds': 'ds_standard', 'ds2': 'ds2_standard'}
            translations.translate_standard_names(h5, snt)

            for k in ('ds', 'ds2', 'ds3', '/root/ds', '/root/ds2', '/root/ds3'):
                if k in ('ds', 'ds3', '/root/ds3'):
                    self.assertNotIn('standard_name', h5[k].attrs)
                else:
                    self.assertIn('standard_name', h5[k].attrs)
            # for k in ('ds', 'ds2', 'ds3', '/root/ds', '/root/ds2', '/root/ds3'):
            #     self.assertIn('standard_name', h5[k])
            h5.sdump()
