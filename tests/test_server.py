import os
import pathlib
import urllib.parse
import tempfile
import sys
import pytest

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False

from h5rdmtoolbox import File


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_server_file_and_resource_endpoint():
    # create a temporary hdf5 file with minimal structure
    tmpdir = pathlib.Path(tempfile.mkdtemp())
    fname = tmpdir / "test_server.h5"
    with File(fname, mode='w') as f:
        f.attrs['title'] = 'Test file'
        g = f.create_group('grp')
        ds = g.create_dataset('data', data=[1, 2, 3])
        ds.attrs['units'] = 'm'

    from h5rdmtoolbox.server import create_app
    app = create_app(fname)
    client = TestClient(app)

    file_key = pathlib.Path(fname).stem
    r = client.get(f"/file/{file_key}", headers={"Accept": "text/turtle"})
    assert r.status_code == 200
    assert 'text/turtle' in r.headers.get('content-type', '')
    assert 'hdf' in r.text or '@prefix' in r.text

    # pick a subject IRI that likely exists: try to find an example from graph
    g = app.state.hdf_graph
    subj = None
    for s in g.subjects():
        subj = s
        break
    assert subj is not None
    encoded = urllib.parse.quote(str(subj), safe='')
    r2 = client.get(f"/resource/{encoded}", headers={"Accept": "text/html"})
    assert r2.status_code == 200
    assert '<html' in r2.text.lower()

    # SPARQL endpoint: basic SELECT
    query = 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5'
    r3 = client.post('/sparql', json={'query': query})
    assert r3.status_code == 200
    assert 'results' in r3.json() or 'head' in r3.json()

    # cleanup
    try:
        os.remove(fname)
    except Exception:
        pass

