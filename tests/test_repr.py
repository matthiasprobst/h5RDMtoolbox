import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox import _repr
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.database import mongo


class TestRepr(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_repr(self):
        # test h5rdmtoolbox._repr.DataSetRepr
        with File(h5tbx.generate_temporary_filename(), 'w') as h5:
            h5.create_dataset('ds', data=3, dtype='int64')
            h5.create_dataset('dsfloat', data=3., dtype='float64')
            h5.create_dataset('str', data='str')

            ssr = _repr.HDF5StructureStrRepr()
            ssr(h5)

            s = ssr.__dataset__('ds', h5['ds'])
            self.assertEqual(s, '\x1b[1mds\x1b[0m 3, dtype: int64')

            s = ssr.__dataset__('dsfloat', h5['dsfloat'])
            self.assertEqual(s, '\x1b[1mdsfloat\x1b[0m 3.0 , dtype: float64')

            s = ssr.__dataset__('str', h5['str'])
            self.assertEqual(s, "\x1b[1mstr\x1b[0m: b'str'")

            shr = _repr.HDF5StructureHTMLRepr()
            shr(h5)

            shr.__dataset__('ds', h5['ds'])
            shr.__dataset__('dsfloat', h5['dsfloat'])
