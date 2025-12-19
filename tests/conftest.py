import os
import pytest
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def _force_cache_dir_for_tests():
    # Keep it stable across all tests in the run
    os.environ.setdefault("MYPACKAGE_CACHE_DIR", str(Path(".cache/zenodo")))
    
    
@pytest.fixture()
def sleep_after():
    """Fixture that causes a delay after executing a test.
    Prevents spamming external providers when used, in case of rate limits.
    """
    import time
    yield
    time.sleep(0.5)