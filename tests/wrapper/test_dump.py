"""Testing common funcitonality across all wrapper classs"""

import unittest

import h5rdmtoolbox as h5tbx


class TestCommon(unittest.TestCase):

    def test_sdump(self):
        h5tbx.use('default')

        print('\n---------------\n')
        with h5tbx.H5File() as h5:
            h5.create_dataset('myvar', data=[1, 2, 4], attrs={'units': 'm/s', 'long_name': 'test var'})
            h5.sdump()

        print('\n---------------\n')
        h5tbx.use('cflike')
        with h5tbx.H5File() as h5:
            h5.create_dataset('myvar', data=[1, 2, 4], attrs={'units': 'm/s', 'long_name': 'test var'})
            h5.sdump()
