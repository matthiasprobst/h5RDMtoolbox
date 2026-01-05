import os
import pathlib
import unittest
from h5rdmtoolbox.catalog import utils

__this_dir__ = pathlib.Path(__file__).parent


class TestUtils(unittest.TestCase):

    @unittest.skipIf(os.name == "nt", "POSIX-only: absolute /home/... paths")
    def test_file_uri_parsing_posix(self):
        res = utils.file_uri_or_path_to_path("file:///home/user/data/file.h5")
        self.assertEqual(res, pathlib.Path("/home/user/data/file.h5"))

    @unittest.skipIf(os.name == "nt", "POSIX-only")
    def test_file_uri_parsing_localhost_posix(self):
        res = utils.file_uri_or_path_to_path("file://localhost/tmp/a%20b.h5")
        self.assertEqual(res, pathlib.Path("/tmp/a b.h5"))

    def test_plain_path_is_returned_as_path(self):
        res = utils.file_uri_or_path_to_path("relative/path/file.h5")
        self.assertEqual(res, pathlib.Path("relative/path/file.h5"))

    def test_accepts_pathlib_path(self):
        p = pathlib.Path("relative/path/file.h5")
        res = utils.file_uri_or_path_to_path(p)
        self.assertEqual(res, p)
        self.assertIsInstance(res, pathlib.Path)

    @unittest.skipIf(os.name != "nt", "Windows-only")
    def test_windows_file_uri_drive_letter(self):
        res = utils.file_uri_or_path_to_path("file:///C:/Temp/a%20b.h5")
        self.assertEqual(res, pathlib.Path(r"C:\Temp\a b.h5"))

    @unittest.skipIf(os.name != "nt", "Windows-only")
    def test_windows_unc_file_uri(self):
        res = utils.file_uri_or_path_to_path("file://server/share/folder/a.h5")
        self.assertEqual(res, pathlib.Path(r"\\server\share\folder\a.h5"))

    def test_fileurl_like_object_if_supported(self):
        """
        Your function optionally supports a FileUrl type via:
            if "FileUrl" in globals() and isinstance(value, FileUrl):
                value = str(value)

        We only run this test if utils exposes FileUrl.
        """
        if not hasattr(utils, "FileUrl"):
            self.skipTest("utils.FileUrl not available in this environment")

        FileUrl = utils.FileUrl
        uri = FileUrl("file:///tmp/a%20b.h5") if os.name != "nt" else FileUrl("file:///C:/Temp/a%20b.h5")

        res = utils.file_uri_or_path_to_path(uri)
        self.assertIsInstance(res, pathlib.Path)
        # percent decoding should have happened
        self.assertNotIn("%", str(res))
