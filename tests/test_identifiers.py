"""test h5rdmtoolbox.user.py"""
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import identifiers


class TestOrcid(unittest.TestCase):

    def test_orcid(self):
        self.assertTrue(identifiers.Orcid('https://orcid.org/0000-0002-1825-0097').validate())
        self.assertFalse(identifiers.Orcid('https://orcid.org/0000-0002-1825-0096').validate())
        self.assertTrue(identifiers.Orcid('0000-0002-1825-0097').validate())
        self.assertTrue(identifiers.Orcid('https://orcid.org/0000-0001-5109-3700').validate())
        self.assertTrue(identifiers.Orcid('https://orcid.org/0000-0002-1694-233X').validate())

    # def test_orcid(self):
    #     o = h5tbx.orcid.KnownOrcids()
    #     o._filename = h5tbx.utils.generate_temporary_filename()
    #     o.load()
    #     self.assertEqual([], o._orcids)
    #     o._orcids = ['1', '2']
    #     o.save()
    #     self.assertTrue(o.filename.exists())
    #
    #     o.add('3')
    #     self.assertEqual(['1', '2', '3'], o.orcids)
    #
    #     o = h5tbx.orcid.ORCID([h5tbx.__author_orcid__])
    #     self.assertIsInstance(o, h5tbx.orcid.ORCID)
    #
    #     o = h5tbx.orcid.ORCID([h5tbx.__author_orcid__, h5tbx.__author_orcid__])
    #     self.assertIsInstance(o, h5tbx.orcid.ORCIDS)
    #     orcids = h5tbx.orcid.ORCIDS([h5tbx.__author_orcid__])
    #     for o in orcids:
    #         self.assertIsInstance(o, h5tbx.orcid.ORCID)
    #     self.assertEqual(h5tbx.__author_orcid__, o)
    #     self.assertIsInstance(orcids[0], h5tbx.orcid.ORCID)
    #     self.assertEqual(h5tbx.__author_orcid__, orcids[0])
    #
    #     print(o.validate())
