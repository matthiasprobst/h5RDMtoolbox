"""test h5rdmtoolbox.user.py"""
import unittest

from h5rdmtoolbox import identifiers


class TestOrcid(unittest.TestCase):

    def test_urn(self):
        self.assertTrue(identifiers.URN('urn:isbn:0143039431').validate())
        self.assertTrue(identifiers.URN('urn:efg://wxyz').validate())
        self.assertTrue(identifiers.URN('urn:issn:1476-4687').validate())
        self.assertFalse(identifiers.URN('xyz:issn:1476-4687').validate())

    def test_rorid(self):
        self.assertTrue(identifiers.RORID('https://ror.org/04wxnsj81').validate())
        self.assertFalse(identifiers.RORID('https://ror.org/?4wxnsj82').validate())
        self.assertTrue(identifiers.RORID('04wxnsj81').validate())
        self.assertEqual(str(identifiers.RORID('04wxnsj81')), 'https://ror.org/04wxnsj81')
        self.assertFalse(identifiers.RORID('https://orcid.org/0000-0002-1825-0097').validate())

        with self.assertRaises(NotImplementedError):
            identifiers.RORID('04wxnsj81').check_checksum()

    def test_from_url(self):
        self.assertIsInstance(identifiers.from_url('https://orcid.org/0000-0002-1825-0097'),
                              identifiers.ORCID)
        # self.assertIsInstance(identifiers.from_url('https://ror.org/04t3en479'),
        #                       identifiers.RORID)

    # def test_gnd(self):
    #     self.assertTrue(identifiers.GND('118540268').validate())
    #     self.assertFalse(identifiers.GND('118540269').validate())

    def test_isbn(self):
        self.assertTrue(identifiers.ISBN10('80-85892-15-4').validate())
        self.assertFalse(identifiers.ISBN10('80/85892-15-4').validate())
        self.assertFalse(identifiers.ISBN10('80-85892-15-8').validate())
        self.assertFalse(identifiers.ISBN10('80-85892-15-X').validate())
        self.assertTrue(identifiers.ISBN13('978-80-85892-15-4').validate())
        self.assertFalse(identifiers.ISBN13('978-80-85892-15-8').validate())
        self.assertFalse(identifiers.ISBN13('978/80-85892-15-4').validate())

    def test_orcid(self):
        self.assertTrue(identifiers.ORCID('https://orcid.org/0000-0002-1825-0097').exists())
        self.assertFalse(identifiers.ORCID('https://orcid.org/1111-0002-1825-0097').exists())
        self.assertTrue(identifiers.ORCID('https://orcid.org/0000-0002-1825-0097').validate())
        self.assertFalse(identifiers.ORCID('https://orcid.org/0000-0002-1825-0096').validate())
        self.assertTrue(identifiers.ORCID('0000-0002-1825-0097').validate())
        self.assertTrue(identifiers.ORCID('https://orcid.org/0000-0001-5109-3700').validate())
        self.assertTrue(identifiers.ORCID('https://orcid.org/0000-0002-1694-233X').validate())

    def test_orcid_cache(self):
        identifiers.KNOWN_ORCID_FILENAME.unlink(missing_ok=True)
        self.assertEqual(len(identifiers.ORCID.get_existing_orcids()), 0)
        identifiers.ORCID('https://orcid.org/0000-0002-1825-0097').exists()
        print(identifiers.ORCID.get_existing_orcids())
        self.assertEqual(len(identifiers.ORCID.get_existing_orcids()), 1)
        self.assertEqual(identifiers.ORCID.get_existing_orcids()[0], 'https://orcid.org/0000-0002-1825-0097')

    # def test_orcid_exists(self):
    # o = h5tbx.orcid.KnownOrcids()
    # o._filename = h5tbx.utils.generate_temporary_filename()
    # o.load()
    # self.assertEqual([], o._orcids)
    # o._orcids = ['1', '2']
    # o.save()
    # self.assertTrue(o.filename.exists())
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
