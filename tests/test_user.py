"""test h5rdmtoolbox.user.py"""
import shutil
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import clean_temp_data
from h5rdmtoolbox._user import UserDir


class TestUser(unittest.TestCase):

    def setUp(self) -> None:
        clean_temp_data(full=True)

    def test_user_dir(self):
        self.assertEqual(h5tbx.UserDir.names, ('root', 'tmp', 'layouts', 'standard_name_tables', 'cache'))
        self.assertTrue('root' in h5tbx.UserDir)

        cache_dir = h5tbx.UserDir['cache']
        h5tbx.UserDir.clear_cache()
        self.assertFalse(cache_dir.exists())

        self.assertTrue(h5tbx.UserDir['cache'].exists())

    def test_user(self):
        self.assertTrue(UserDir['root'].is_dir())
        bak_dir = UserDir['root'].parent / 'bak'
        if bak_dir.exists():
            shutil.rmtree(bak_dir)
        bak_dir.mkdir(exist_ok=True, parents=True)
        for d in UserDir['root'].iterdir():
            if d.is_dir():
                try:
                    shutil.copytree(d, bak_dir / d.name)
                except shutil.Error:
                    print(f'shutil.Error: {d}')
            else:
                shutil.copy(d, bak_dir / d.name)

        shutil.rmtree(UserDir['layouts'])

        try:
            shutil.rmtree(UserDir['tmp'])
        except PermissionError:
            print(f'PermissionError: {UserDir["tmp"]}')
        self.assertTrue(UserDir['root'].exists())
        shutil.rmtree(bak_dir)
