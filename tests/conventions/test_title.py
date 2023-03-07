"""test h5rdmtolbox.conventions.cflike.title"""
import unittest

import h5rdmtoolbox
from h5rdmtoolbox.conventions.cflike import title


class TestTitle(unittest.TestCase):
    """Test h5rdmtolbox.conventions.cflike.title"""

    def test_title(self):
        """Test title attribute"""
        h5rdmtoolbox.use('cflike')
        with h5rdmtoolbox.File() as h5:
            with self.assertRaises(title.TitleError):
                h5.title = ' test'
            with self.assertRaises(title.TitleError):
                h5.title = 'test '
            with self.assertRaises(title.TitleError):
                h5.title = '9test'
            h5.title = 'test'
            self.assertEqual(h5.title, 'test')
            del h5.title
            self.assertEqual(h5.title, None)
