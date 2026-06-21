import os
import pathlib

import pytest

import h5rdmtoolbox as h5tbx


def pytest_collection_modifyitems(config, items):
    """Skip public Wikidata Query Service tests unless explicitly enabled."""
    if os.environ.get("H5RDMTOOLBOX_RUN_WIKIDATA_TESTS") == "1":
        return

    skip_wikidata = pytest.mark.skip(
        reason="set H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1 to run Wikidata tests"
    )
    for item in items:
        if "wikidata" in item.keywords:
            item.add_marker(skip_wikidata)


@pytest.fixture(scope="session", autouse=True)
def _force_cache_dir_for_tests():
    os.environ.setdefault("MYPACKAGE_CACHE_DIR", str(pathlib.Path(".cache/zenodo")))


@pytest.fixture(autouse=True)
def reset_convention():
    """Reset convention before each test."""
    h5tbx.use(None)
    yield
    h5tbx.use(None)


@pytest.fixture
def tmp_h5_file(tmp_path):
    """Create a temporary HDF5 file.

    Yields
    ------
    h5tbx.File
        Open HDF5 file in write mode. Auto-cleaned up after test.
    """
    filepath = tmp_path / "test.h5"
    with h5tbx.File(filepath, "w") as h5:
        yield h5


@pytest.fixture
def tmp_h5_group(tmp_h5_file):
    """Create a temp HDF5 file with a group.

    Yields
    ------
    tuple
        (h5tbx.File, h5tbx.Group) tuple
    """
    h5 = tmp_h5_file
    grp = h5.create_group("test_group")
    yield h5, grp


@pytest.fixture
def tmp_h5_dataset(tmp_h5_file):
    """Create a temp HDF5 file with a dataset.

    Yields
    ------
    tuple
        (h5tbx.File, h5tbx.Dataset) tuple
    """
    import numpy as np

    h5 = tmp_h5_file
    ds = h5.create_dataset("test_data", data=np.array([1, 2, 3]))
    yield h5, ds
