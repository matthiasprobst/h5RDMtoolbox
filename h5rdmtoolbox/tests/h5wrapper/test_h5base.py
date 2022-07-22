import unittest

from h5rdmtoolbox.h5wrapper import H5Base


class TestH5Base(unittest.TestCase):

    def test_Layout(self):
        self.assertTrue(H5Base.Layout.filename.exists())
        self.assertEqual(H5Base.Layout.filename.stem, 'H5Base')
        with H5Base() as h5:
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 0)
            h5.title = 'my title'
            n_issuess = h5.check()
            self.assertEqual(n_issuess, 0)

    def test_create_dataset_from_image(self):
        # just call the tutorial
        from h5rdmtoolbox import tutorial
        with tutorial.get_H5PIV('vortex_snapshot', 'r+') as h5:
            pass
