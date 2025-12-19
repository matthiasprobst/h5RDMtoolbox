import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _force_cache_dir_for_tests():
    # Keep it stable across all tests in the run
    os.environ.setdefault("MYPACKAGE_CACHE_DIR", str(Path(".cache/zenodo")))
