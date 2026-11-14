"""Catalog validation uses the shared engine only when explicitly requested."""

import rdflib
import pytest

from h5rdmtoolbox.catalog import CatalogManager, InMemoryRDFStore


def test_store_validation_is_explicit(tmp_path):
    source = tmp_path / "person.ttl"
    source.write_text('@prefix ex: <https://example.org/> . ex:person a ex:Person .')
    shapes = rdflib.Graph().parse(data='''
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix ex: <https://example.org/> .
        ex:Shape a sh:NodeShape; sh:targetClass ex:Person;
            sh:property [ sh:path ex:name; sh:minCount 1 ] .
    ''', format="turtle")
    store = InMemoryRDFStore(tmp_path / "store")
    store.register_shacl_shape("person", shacl_data=shapes)
    other = InMemoryRDFStore(tmp_path / "other-store")
    assert not other.__shacl_shapes__
    assert other.upload_file(source, validate=True)
    assert store.upload_file(source)
    with pytest.raises(ValueError, match="SHACL validation failed"):
        store.upload_file(source, validate=True)


def test_catalog_returns_shared_validation_result(tmp_path):
    source = tmp_path / "catalog.ttl"
    source.write_text('@prefix dcat: <http://www.w3.org/ns/dcat#> . '
                      '<https://example.org/catalog> a dcat:Catalog .')
    result = CatalogManager.validate_catalog(source)
    assert not result.conforms
    assert result.violations
    assert isinstance(result.results_graph, rdflib.Graph)
