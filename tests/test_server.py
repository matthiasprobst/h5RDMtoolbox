import pathlib
import tempfile
import urllib.parse
import json

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
    assert "/server_test.h5/query" in response.text
    assert "/server_test.h5/metrics" in response.text
    assert "/server_test.h5/shacl" in response.text
    assert 'action="/resolve"' in response.text
    assert 'name="iri"' in response.text
    assert ">Resolve<" in response.text
    assert ">Graph<" in response.text
    assert ">Query<" in response.text
    assert ">Metrics<" in response.text
    assert ">SHACL<" in response.text


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
def test_file_subject_endpoint_returns_turtle_for_hdf5_object(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/grp?format=ttl")

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "hdf:Group" in response.text
    assert 'hdf:name "/grp"' in response.text
    assert "hdf:File" not in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_returns_html_by_default(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/grp")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<h1" in response.text
    assert "hdf:name" in response.text
    assert "/server_test.h5/grp?format=ttl" in response.text
    assert "/server_test.h5/grp?format=jsonld" in response.text
    assert "/resolve?iri=http%3A%2F%2Fpurl.allotrope.org%2Fontologies%2Fhdf5%2F1.8%23Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_uses_accept_header(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/grp", headers={"accept": "application/ld+json"})

    assert response.status_code == 200
    assert "application/ld+json" in response.headers["content-type"]
    assert '"@id"' in response.text
    assert "server_test.h5/grp" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_format_overrides_accept_header(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/grp?format=ttl", headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_resolves_file_uri_subject(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename, file_uri="https://example.org#"))
    response = client.get("/server_test.h5/grp?prefix=ex&format=ttl")

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "<https://example.org#server_test.h5/grp>" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_resolves_encoded_file_uri_query(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/grp?file_uri=https://example.org%23&prefix=ex&format=ttl")

    assert response.status_code == 200
    assert "<https://example.org#server_test.h5/grp>" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_subject_endpoint_returns_404_for_unknown_subject(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/missing")

    assert response.status_code == 404
    assert "Unknown RDF subject" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_endpoint_returns_turtle_for_matching_external_iri(hdf_filename):
    from h5rdmtoolbox.server import create_app

    iri = "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
        local_iri_patterns=["https://doi.org/10.5281/zenodo.*"],
    ))
    response = client.get(f"/resolve/{urllib.parse.quote(iri, safe='')}?format=ttl")

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "<https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp>" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
@pytest.mark.parametrize("path", ["/", "/resolve"])
def test_resolve_query_parameter_returns_turtle_for_matching_external_iri(hdf_filename, path):
    from h5rdmtoolbox.server import create_app

    iri = "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp"
    parameter = "resolve" if path == "/" else "iri"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
        local_iri_patterns=["https://doi.org/10.5281/zenodo.*"],
    ))
    response = client.get(path, params={parameter: iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "<https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp>" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_query_parameter_does_not_require_local_iri_pattern(hdf_filename):
    from h5rdmtoolbox.server import create_app

    iri = "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
    ))
    response = client.get("/", params={"resolve": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "<https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp>" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_query_parameter_supports_jsonld_format(hdf_filename):
    from h5rdmtoolbox.server import create_app

    iri = "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
    ))
    response = client.get("/resolve", params={"iri": iri, "format": "jsonld"})

    assert response.status_code == 200
    assert "application/ld+json" in response.headers["content-type"]
    assert '"@id"' in response.text
    assert "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_endpoint_rejects_non_matching_external_iri(hdf_filename):
    from h5rdmtoolbox.server import create_app

    iri = "https://example.org/server_test.h5/grp"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
        local_iri_patterns=["https://doi.org/10.5281/zenodo.*"],
    ))
    response = client.get(f"/resolve/{urllib.parse.quote(iri, safe='')}")

    assert response.status_code == 404
    assert "Unknown RDF subject" in response.text


class _FakeHTTPResponse:
    def __init__(self, data: bytes):
        self.data = data

    def read(self):
        return self.data

    def geturl(self):
        return "https://example.org/resource"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_uses_zenodo_doi_fallback_for_fragment_iri(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    iri = "https://doi.org/10.5072/zenodo.987654321#observable_property/T1"
    calls = []
    record = {
        "files": [
            {"key": "ignored.txt", "links": {"self": "https://sandbox.zenodo.org/api/records/987654321/files/ignored/content"}},
            {"key": "metadata.ttl", "links": {"self": "https://sandbox.zenodo.org/api/records/987654321/files/metadata/content"}},
        ]
    }
    ttl = f"""@prefix ex: <https://example.org/> .
<{iri}> a ex:Observable ;
  ex:name "T1" .
"""

    def fake_urlopen(url, timeout=0):
        calls.append(url)
        if url == "https://sandbox.zenodo.org/api/records/987654321":
            return _FakeHTTPResponse(json.dumps(record).encode("utf-8"))
        if url.endswith("/metadata/content"):
            return _FakeHTTPResponse(ttl.encode("utf-8"))
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get("/resolve", params={"iri": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "ex:Observable" in response.text
    assert "T1" in response.text
    assert calls[0] == "https://sandbox.zenodo.org/api/records/987654321"
    assert not any(call.endswith("/ignored/content") for call in calls)


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_uses_zenodo_record_url_fallback(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    iri = "https://zenodo.org/records/987654322#observable_property/T1"
    record = {
        "files": [
            {"key": "metadata.ttl", "links": {"self": "https://zenodo.org/api/records/987654322/files/metadata/content"}},
        ]
    }
    ttl = f"""@prefix ex: <https://example.org/> .
<{iri}> ex:name "T1" .
"""

    def fake_urlopen(url, timeout=0):
        if url == "https://zenodo.org/api/records/987654322":
            return _FakeHTTPResponse(json.dumps(record).encode("utf-8"))
        if url.endswith("/metadata/content"):
            return _FakeHTTPResponse(ttl.encode("utf-8"))
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get("/resolve", params={"iri": iri, "format": "jsonld"})

    assert response.status_code == 200
    assert "application/ld+json" in response.headers["content-type"]
    assert "https://zenodo.org/records/987654322#observable_property/T1" in response.text
    assert "T1" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_merges_local_and_zenodo_fragment_data(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    iri = "https://doi.org/10.5072/zenodo.987654324#server_test.h5/grp"
    record = {
        "files": [
            {"key": "metadata.ttl", "links": {"self": "https://sandbox.zenodo.org/api/records/987654324/files/metadata/content"}},
        ]
    }
    ttl = f"""@prefix ex: <https://example.org/> .
<{iri}> ex:source "zenodo" .
"""

    def fake_urlopen(url, timeout=0):
        if url == "https://sandbox.zenodo.org/api/records/987654324":
            return _FakeHTTPResponse(json.dumps(record).encode("utf-8"))
        if url.endswith("/metadata/content"):
            return _FakeHTTPResponse(ttl.encode("utf-8"))
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5072/zenodo.987654324#",
    ))
    response = client.get("/resolve", params={"iri": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "hdf:Group" in response.text
    assert 'hdf:name "/grp"' in response.text
    assert 'ex:source "zenodo"' in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_does_not_use_zenodo_fallback_without_fragment(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    def fake_urlopen(url, timeout=0):
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get(
        "/resolve",
        params={"iri": "https://doi.org/10.5072/zenodo.987654323", "format": "ttl"},
    )

    assert response.status_code == 404
    assert "Unknown RDF subject" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_uses_known_ontology_registry_for_fragment_iri(monkeypatch, caplog, hdf_filename):
    import h5rdmtoolbox.server as server

    caplog.set_level("INFO", logger="h5rdmtoolbox.server")
    iri = "https://matthiasprobst.github.io/ssno#StandardName"
    ontology_iri = "https://matthiasprobst.github.io/ssno/#StandardName"
    ttl = f"""@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<{ontology_iri}> a rdfs:Class ;
  rdfs:label "Standard name" .
"""
    calls = []

    class RegistryResponse(_FakeHTTPResponse):
        def geturl(self):
            return "https://matthiasprobst.github.io/ssno/ssno.ttl"

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url if hasattr(request, "full_url") else request)
        url = request.full_url if hasattr(request, "full_url") else request
        if url == "https://matthiasprobst.github.io/ssno/ssno.ttl":
            return RegistryResponse(ttl.encode("utf-8"))
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get("/resolve", params={"iri": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "rdfs:Class" in response.text
    assert "Standard name" in response.text
    assert calls == [
        "https://matthiasprobst.github.io/ssno/ssno.ttl",
    ]
    assert "Known ontology candidates for https://matthiasprobst.github.io/ssno#StandardName" in caplog.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_uses_ontology_document_for_fragment_iri(monkeypatch, caplog, hdf_filename):
    import h5rdmtoolbox.server as server

    caplog.set_level("INFO", logger="h5rdmtoolbox.server")
    iri = "https://example.org/ontology#ExampleClass"
    ontology_iri = "https://example.org/ontology/#ExampleClass"
    html = b"""<!doctype html>
<html><body><a href="ontology.ttl">TTL</a></body></html>
"""
    ttl = f"""@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<{ontology_iri}> a rdfs:Class ;
  rdfs:label "Example class" .
"""
    calls = []

    class OntologyResponse(_FakeHTTPResponse):
        def geturl(self):
            return "https://example.org/ontology/"

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url if hasattr(request, "full_url") else request)
        url = request.full_url if hasattr(request, "full_url") else request
        if url == "https://example.org/ontology/":
            return OntologyResponse(html)
        if url == "https://example.org/ontology/ontology.ttl":
            return OntologyResponse(ttl.encode("utf-8"))
        raise AssertionError(f"Unexpected download: {url}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get("/resolve", params={"iri": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "rdfs:Class" in response.text
    assert "Example class" in response.text
    assert calls == [
        "https://example.org/ontology/",
        "https://example.org/ontology/ontology.ttl",
    ]
    assert "Ontology subject candidates for https://example.org/ontology#ExampleClass" in caplog.text
    assert "Loading linked RDF serialization https://example.org/ontology/ontology.ttl" in caplog.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_does_not_use_ontology_document_without_fragment(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    def fake_urlopen(request, timeout=0):
        raise AssertionError(f"Unexpected download: {request}")

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get(
        "/resolve",
        params={"iri": "https://matthiasprobst.github.io/ssno/", "format": "ttl"},
    )

    assert response.status_code == 404
    assert "Unknown RDF subject" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_resolve_uses_wikidata_direct_claims(monkeypatch, hdf_filename):
    import h5rdmtoolbox.server as server

    iri = "https://www.wikidata.org/wiki/Q42"
    results = {
        "results": {
            "bindings": [
                {
                    "property": {"type": "uri", "value": "http://www.wikidata.org/prop/direct/P31"},
                    "value": {"type": "uri", "value": "http://www.wikidata.org/entity/Q5"},
                },
                {
                    "property": {"type": "uri", "value": "http://www.wikidata.org/prop/direct/P569"},
                    "value": {
                        "type": "literal",
                        "value": "1952-03-11T00:00:00Z",
                        "datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
                    },
                },
            ]
        }
    }

    def fake_urlopen(request, timeout=0):
        url = request.full_url if hasattr(request, "full_url") else request
        assert url.startswith("https://query.wikidata.org/sparql?")
        return _FakeHTTPResponse(json.dumps(results).encode("utf-8"))

    monkeypatch.setattr(server.urllib.request, "urlopen", fake_urlopen)
    client = TestClient(server.create_app(hdf_filename, file_uri="https://example.org/not-this#"))
    response = client.get("/resolve", params={"iri": iri, "format": "ttl"})

    assert response.status_code == 200
    assert "text/turtle" in response.headers["content-type"]
    assert "P31" in response.text
    assert "<http://www.wikidata.org/entity/Q5>" in response.text
    assert "1952-03-11T00:00:00+00:00" in response.text or "1952-03-11T00:00:00Z" in response.text


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
def test_file_graph_endpoint_links_matching_external_iris_to_local_resolver(hdf_filename):
    from h5rdmtoolbox.server import create_app

    iri = "https://doi.org/10.5281/zenodo.17572275#server_test.h5/grp"
    client = TestClient(create_app(
        hdf_filename,
        file_uri="https://doi.org/10.5281/zenodo.17572275#",
        local_iri_patterns=["https://doi.org/10.5281/zenodo.*"],
    ))
    response = client.get("/server_test.h5/graph")

    assert response.status_code == 200
    assert "Open local TTL" in response.text
    assert f"/resolve?iri={urllib.parse.quote(iri, safe='')}" in response.text


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
def test_file_query_endpoint_returns_query_form(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/query")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SPARQL Query" in response.text
    assert 'id="sparql-query"' in response.text
    assert 'id="sparql-result"' in response.text
    assert "sample-query-button" in response.text
    assert "Standard names" in response.text
    assert "RDF types" in response.text
    assert "Units" in response.text
    assert "ssno:standardName" in response.text
    assert "ssno:StandardName" in response.text
    assert "sampleQueries" in response.text
    assert "SELECT ?subject ?predicate ?object" in response.text
    assert "Run the example query" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_query_endpoint_runs_select_query(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get(
        "/server_test.h5/query",
        params={"query": "SELECT ?type WHERE { ?s a ?type . } LIMIT 5"},
    )

    assert response.status_code == 200
    assert 'class="result-table"' in response.text
    assert "<th>type</th>" in response.text
    assert "hdf:File" in response.text
    assert "hdf:Group" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_shacl_endpoint_returns_validation_form(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/shacl")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SHACL Validation" in response.text
    assert 'id="shacl-shapes"' in response.text
    assert 'id="shacl-result"' in response.text
    assert "hdf:FileShape" in response.text
    assert "sh:minCount 1" in response.text
    assert "Run the default shape" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_shacl_endpoint_runs_validation(hdf_filename):
    from h5rdmtoolbox.server import create_app

    shapes = """@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

hdf:FileShape
  a sh:NodeShape ;
  sh:targetClass hdf:File ;
  sh:property [
    sh:path hdf:rootGroup ;
    sh:minCount 1 ;
  ] .
"""
    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/shacl", params={"shapes": shapes})

    assert response.status_code == 200
    assert "Conforms" in response.text
    assert "Validation Report" in response.text
    assert "sh:conforms true" in response.text


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not installed")
def test_file_metrics_endpoint_returns_graph_metrics(hdf_filename):
    from h5rdmtoolbox.server import create_app

    client = TestClient(create_app(hdf_filename))
    response = client.get("/server_test.h5/metrics")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Graph Metrics" in response.text
    assert "Knowledge Graph Metrics" in response.text
    assert "Total triples" in response.text
    assert "Literal count" in response.text
    assert "Distinct subjects" in response.text
    assert "Distinct predicates" in response.text
    assert "Distinct objects" in response.text
    assert "IRI count" in response.text
    assert "Blank node count" in response.text
    assert "Avg triples / subject" in response.text
    assert "Connected components" in response.text
    assert "Largest distance" in response.text
    assert "Label coverage" in response.text
    assert "owl:sameAs links" in response.text
    assert "Top Predicates" in response.text
    assert "Rare Predicates" in response.text
    assert "Predicate Usage Distribution" in response.text
    assert "RDF Classes" in response.text
    assert "Top Nodes by Out-Degree" in response.text
    assert "Top Nodes by In-Degree" in response.text
    assert "Datatype Distribution" in response.text
    assert "Language Tags" in response.text
    assert "Literal Quality" in response.text
    assert "Label Readability" in response.text
    assert "Data Quality" in response.text
    assert "External Namespaces" in response.text
    assert "hdf:File" in response.text
    assert "hdf:Group" in response.text
    assert "hdf:rootGroup" in response.text


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
