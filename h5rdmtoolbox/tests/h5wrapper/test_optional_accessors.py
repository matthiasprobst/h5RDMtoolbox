"""Testing common funcitonality across all wrapper classs"""

import unittest
from importlib.metadata import metadata

from h5rdmtoolbox.h5wrapper.standardized_attributes import software

import h5rdmtoolbox as h5tbx
class TestOptAccessors(unittest.TestCase):

    def test_software(self):
        meta = metadata('numpy')

        s = software.Software(meta['Name'], version=meta['Version'], url=meta['Home-page'],
                              description=meta['Summary'])

        with h5tbx.H5File() as h5:
            h5.software = s
            h5.sdump()
