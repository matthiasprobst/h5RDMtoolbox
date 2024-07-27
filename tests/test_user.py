"""test h5rdmtoolbox.user.py"""
import datetime
import os
import shutil
import time
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import clean_temp_data
from h5rdmtoolbox.user import UserDir


class TestUser(unittest.TestCase):

    def setUp(self) -> None:
        clean_temp_data(full=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cache_dir = (h5tbx.UserDir['cache'].exists(), h5tbx.UserDir['cache'])
        convention_dir = (h5tbx.UserDir['convention'].exists(), h5tbx.UserDir['convention'])
        snt_dir = (h5tbx.UserDir['standard_name_tables'].exists(), h5tbx.UserDir['standard_name_tables'])
        layouts_dir = (h5tbx.UserDir['layouts'].exists(), h5tbx.UserDir['layouts'])
        tmp_dir = (h5tbx.UserDir['tmp'].exists(), h5tbx.UserDir['tmp'])

        h5tbx.UserDir.reset()
        if cache_dir[0]:
            assert not cache_dir[1].exists(), 'UserDir.reset() failed to remove cache directory'
        if convention_dir[0]:
            assert not convention_dir[1].exists(), 'UserDir.reset() failed to remove convention directory'
        if snt_dir[0]:
            assert not snt_dir[1].exists(), 'UserDir.reset() failed to remove standard_name_tables directory'
        if layouts_dir[0]:
            assert not layouts_dir[1].exists(), 'UserDir.reset() failed to remove layouts directory'
        if tmp_dir[0]:
            assert not tmp_dir[1].exists(), 'UserDir.reset() failed to remove tmp directory'

    def test_user_dir(self):
        self.assertListEqual(sorted(h5tbx.UserDir.names),
                             sorted(('root', 'tmp', 'layouts', 'repository',
                                     'standard_name_tables', 'cache', 'convention')))
        self.assertTrue('root' in h5tbx.UserDir)

        cache_dir = h5tbx.UserDir['cache']
        h5tbx.UserDir.clear_cache(delta_days=0)
        self.assertFalse(cache_dir.exists())

        self.assertTrue(h5tbx.UserDir['cache'].exists())

        # create cache with file from the past
        cache_dir = h5tbx.UserDir['cache']
        filename = cache_dir / 'test.txt'
        with open(filename, 'w') as f:
            f.write('test')
        timestamp = datetime.datetime.now() - datetime.timedelta(days=2)
        epoch_time = time.mktime(timestamp.timetuple())
        os.utime(filename, (epoch_time, epoch_time))
        self.assertTrue(cache_dir.exists())
        h5tbx.UserDir.clear_cache(delta_days=1, utime=True)
        self.assertFalse(filename.exists())

        with open(filename, 'w') as f:
            f.write('test')
        os.utime(filename, (epoch_time, epoch_time))
        h5tbx.UserDir.clear_cache(delta_days=3, utime=True)
        self.assertTrue(filename.exists())
        filename.unlink()

        with self.assertRaises(ValueError):
            h5tbx.UserDir._get_dir('invalid')
        if h5tbx.UserDir.user_dirs['standard_name_tables'].exists():
            shutil.rmtree(h5tbx.UserDir.user_dirs['standard_name_tables'])
        d = h5tbx.UserDir._get_dir('standard_name_tables')
        self.assertTrue(d.exists())
        self.assertTrue((d / 'fluid-v1.yml').exists())

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

        if UserDir['layouts'].exists():
            shutil.rmtree(UserDir['layouts'])

        try:
            shutil.rmtree(UserDir['tmp'])
        except PermissionError:
            print(f'PermissionError: {UserDir["tmp"]}')
        self.assertTrue(UserDir['root'].exists())
        shutil.rmtree(bak_dir)
