"""test h5rdmtoolbox.user.py"""
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import orcid


class TestOrcid(unittest.TestCase):

    def test_orcid(self):
        o = h5tbx.orcid.KnownOrcids()
        o._filename = h5tbx.utils.generate_temporary_filename()
        o.load()
        self.assertEqual([], o._orcids)
        o._orcids = ['1', '2']
        o.save()
        self.assertTrue(o.filename.exists())

        o.add('3')
        self.assertEqual(['1', '2', '3'], o.orcids)

        o = h5tbx.orcid.ORCID([h5tbx.__author_orcid__])
        self.assertIsInstance(o, h5tbx.orcid.ORCID)

        o = h5tbx.orcid.ORCID([h5tbx.__author_orcid__, h5tbx.__author_orcid__])
        self.assertIsInstance(o, h5tbx.orcid.ORCID)
        orcids = h5tbx.orcid.ORCIDS([h5tbx.__author_orcid__])
        for o in orcids:
            self.assertIsInstance(o, h5tbx.orcid.ORCID)
        self.assertEqual(h5tbx.__author_orcid__, o)
        self.assertIsInstance(orcids[0], h5tbx.orcid.ORCID)
        self.assertEqual(h5tbx.__author_orcid__, orcids[0])
