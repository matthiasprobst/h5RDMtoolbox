"""Explicit application-directory operations."""
import pytest
from h5rdmtoolbox.user import UserDir


def test_directories_are_created_on_request():
    assert set(UserDir.names) == {'root', 'tmp', 'repository', 'cache'}
    assert UserDir['tmp'].is_dir()
    assert UserDir['repository'].is_dir()
    with pytest.raises(ValueError):
        UserDir['convention']


def test_explicit_cache_cleanup():
    cache = UserDir['cache']
    (cache / 'sample').write_text('cached')
    UserDir.clear_cache(0)
    assert not cache.exists()
    assert UserDir['cache'].is_dir()
