import pathlib
import tempfile

import h5py
import pytest
import rdflib

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
    assert "/server_test.h5/jsonld" in response.text
    assert "/server_test.h5/nt" in response.text
    assert "/server_test.h5/xml" in response.text
    assert "/server_test.h5/graph" in response.text
    assert ">Graph<" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_ttl_endpoint_returns_form_and_dump(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<select name="structural">' in response.text
    assert '<select name="contextual">' in response.text
    assert 'name="file_uri"' in response.text
    assert 'name="prefix"' in response.text
    assert "raw=true" in response.text
    assert "Copy to clipboard" in response.text
    assert 'id="serialization-output"' in response.text
    assert "@prefix hdf:" in response.text
    assert "hdf:File" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_ttl_endpoint_returns_raw_turtle(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?raw=true")

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
    assert "&lt;https://example.org/data/server_test.h5&gt;" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_ttl_endpoint_binds_file_uri_prefix(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?raw=true&file_uri=https://example.org/data/&prefix=ex")

    assert response.status_code == 200
    assert "@prefix ex: <https://example.org/data/> ." in response.text
    assert "ex:server_test.h5" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_ttl_endpoint_rejects_invalid_prefix(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?file_uri=https://example.org/data/&prefix=1bad")

    assert response.status_code == 400
    assert "prefix must start" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_ttl_endpoint_rejects_empty_selection(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/ttl?structural=false&contextual=false")

    assert response.status_code == 400
    assert "At least one of structural or contextual must be True" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
@pytest.mark.parametrize(
    ("path", "content_type", "expected"),
    [
        ("/server_test.h5/jsonld?raw=true", "application/ld+json", '"@id"'),
        ("/server_test.h5/nt?raw=true", "application/n-triples", "http://purl.allotrope.org/ontologies/hdf5/1.8#File"),
        ("/server_test.h5/xml?raw=true", "application/rdf+xml", "rdf:RDF"),
    ],
)
def test_file_format_endpoints_return_raw_formats(hdf_filename, path, content_type, expected):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    assert expected in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_graph_endpoint_returns_interactive_page(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/graph")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "vis-network" in response.text
    assert "new vis.Network" in response.text
    assert 'id="graph-form"' in response.text
    assert "graphForm.requestSubmit();" in response.text
    assert 'id="node-details"' in response.text
    assert 'network.on("click"' in response.text
    assert 'id="hidden-node-toggle"' in response.text
    assert 'id="hidden-node-list"' in response.text
    assert 'class="hide-node-button">Hide</button>' in response.text
    assert "hiddenNodeIds.add(nodeId);" in response.text
    assert "hiddenNodeIds.delete(nodeId);" in response.text
    assert "refreshVisibleGraph();" in response.text
    assert "grid-template-columns: minmax(7rem, max-content) minmax(0, 1fr);" in response.text
    assert '<section class="graph-panel">' in response.text
    assert "height: 100dvh;" in response.text
    assert "height: 100%;" in response.text
    assert '"nodes":' in response.text
    assert '"edges":' in response.text
    assert '"groups":' in response.text
    assert '"literals":' in response.text
    assert '"group": "literal"' not in response.text
    assert '"group": "class:hdf:File"' in response.text
    assert '"group": "class:hdf:Group"' in response.text
    assert '"class:hdf:File"' in response.text
    assert '"class:hdf:Group"' in response.text
    assert '"label": "hdf:File"' in response.text
    assert '"label": "hdf:rootGroup"' in response.text
    assert 'name="mode" value="both" checked' in response.text
    assert 'name="mode" value="structural"' in response.text
    assert 'name="mode" value="contextual"' in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_graph_endpoint_accepts_mode_and_prefix_options(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/graph?mode=structural&file_uri=https://example.org/data/&prefix=ex")

    assert response.status_code == 200
    assert 'name="mode" value="structural" checked' in response.text
    assert 'value="https://example.org/data/"' in response.text
    assert 'value="ex"' in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_graph_endpoint_rejects_invalid_mode(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/graph?mode=none")

    assert response.status_code == 400
    assert "mode must be one of" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_graph_uses_standard_prefixes_for_compact_labels(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    graph = rdflib.Graph()
    dataset = rdflib.URIRef("https://doi.org/10.5281/zenodo.12345")
    graph.add((dataset, rdflib.RDF.type, rdflib.URIRef("http://www.w3.org/ns/dcat#Dataset")))
    graph.add((dataset, rdflib.URIRef("http://xmlns.com/foaf/0.1/name"), rdflib.Literal("example")))
    graph.add((dataset, rdflib.URIRef("http://qudt.org/schema/qudt/unit"), rdflib.URIRef("http://qudt.org/vocab/unit/M")))
    graph.add((dataset, rdflib.URIRef("http://purl.org/dc/terms/identifier"), rdflib.URIRef("https://zenodo.org/records/12345")))

    monkeypatch.setattr(server, "get_ld", lambda *args, **kwargs: graph)
    client = TestClient(server.create_app(hdf_filename))
    response = client.get("/server_test.h5/graph")

    assert response.status_code == 200
    assert '"label": "doi:10.5281/zenodo.12345"' in response.text
    assert '"label": "dcat:Dataset"' in response.text
    assert '"predicate": "foaf:name"' in response.text
    assert '"label": "qudt:unit"' in response.text
    assert '"label": "unit:M"' in response.text
    assert '"label": "dcterms:identifier"' in response.text
    assert '"label": "zenodo:12345"' in response.text


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

    ttl_response = client.get("/second.hdf/ttl?raw=true")
    assert ttl_response.status_code == 200
    assert "hdf:File" in ttl_response.text
