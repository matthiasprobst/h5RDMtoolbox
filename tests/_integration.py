"""Collection policy for live services, independent of toolbox initialization."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Require independent opt-ins for external queries and Zenodo uploads."""
    skip_wikidata = pytest.mark.skip(
        reason="set H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1 to run Wikidata tests"
    )
    skip_upload = pytest.mark.skip(
        reason="set H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1 and ZENODO_SANDBOX_API_TOKEN to run live uploads"
    )
    skip_zenodo_read = pytest.mark.skip(
        reason="set H5RDMTOOLBOX_RUN_ZENODO_READ_TESTS=1 to run live Zenodo reads"
    )
    for item in items:
        if "zenodo_read" in item.keywords and os.environ.get("H5RDMTOOLBOX_RUN_ZENODO_READ_TESTS") != "1":
            item.add_marker(skip_zenodo_read)
        if "wikidata" in item.keywords and os.environ.get("H5RDMTOOLBOX_RUN_WIKIDATA_TESTS") != "1":
            item.add_marker(skip_wikidata)
        if "zenodo_upload" in item.keywords and not (
            os.environ.get("H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS") == "1"
            and os.environ.get("ZENODO_SANDBOX_API_TOKEN", "").strip()
        ):
            item.add_marker(skip_upload)
