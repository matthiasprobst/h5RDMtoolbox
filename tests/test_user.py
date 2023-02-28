"""test h5rdmtoolbox.user.py"""
import shutil
import unittest

from h5rdmtoolbox._user import UserDir


class TestUser(unittest.TestCase):

    def test_user(self):
        self.assertTrue(UserDir['root'].is_dir())
        bak_dir = UserDir['root'].parent / 'bak'
        shutil.rmtree(bak_dir, ignore_errors=True)
        shutil.copytree(UserDir['root'], UserDir['root'].parent / 'bak')
        shutil.rmtree(UserDir['layouts'])
        shutil.rmtree(UserDir['standard_name_tables'])
        shutil.rmtree(UserDir['standard_name_table_translations'])
        shutil.rmtree(UserDir['tmp'])
        self.assertTrue(UserDir['root'].exists())
        shutil.rmtree(bak_dir)

