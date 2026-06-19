import pathlib
import tempfile

import h5py
import pytest

try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False


@pytest.fixture()
def hdf_filename():
    tmpdir = pathlib.Path(tempfile.mkdtemp())
    filename = tmpdir / "server_test.h5"
    with h5py.File(filename, "w") as h5:
        h5.create_group("grp")
    return filename


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_landing_page_lists_hdf5_files(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))

    response = client.get("/")

    assert response.status_code == 200
    assert "server_test.h5" in response.text
    assert "/server_test.h5/ttl" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_ttl_endpoint_returns_turtle(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl")

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "@prefix hdf:" in response.text
    assert "hdf:File" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_ttl_endpoint_accepts_query_options(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?contextual=false&file_uri=https://example.org/data/")

    assert response.status_code == 200
    assert "<https://example.org/data/server_test.h5>" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_ttl_endpoint_rejects_empty_selection(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?structural=false&contextual=false")

    assert response.status_code == 400
    assert "At least one of structural or contextual must be True" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_create_app_discovers_hdf5_files(monkeypatch, hdf_filename):
    from h5rdmtoolbox.server import create_app

    with h5py.File(hdf_filename.parent / "second.hdf", "w"):
        pass
    with h5py.File(hdf_filename.parent / "third.hdf5", "w"):
        pass
    (hdf_filename.parent / "ignored.txt").write_text("not hdf5")
    monkeypatch.chdir(hdf_filename.parent)
    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    assert "server_test.h5" in response.text
    assert "second.hdf" in response.text
    assert "third.hdf5" in response.text
    assert "ignored.txt" not in response.text

    ttl_response = client.get("/second.hdf/ttl")
    assert ttl_response.status_code == 200
    assert "hdf:File" in ttl_response.text
