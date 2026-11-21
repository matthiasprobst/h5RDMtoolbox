"""Public catalog behavior across query and storage module boundaries."""

from unittest.mock import Mock

import pytest
import rdflib
from rdflib.compare import isomorphic

from h5rdmtoolbox import catalog
from h5rdmtoolbox.catalog import core


def test_compatibility_exports_preserve_class_identity():
    from h5rdmtoolbox.catalog import abstracts, queries, store_manager
    from h5rdmtoolbox.catalog.stores import memory, sparql, sql

    definitions = {
        abstracts: ("DataStore", "MetadataStore", "RDFStore", "Store"),
        queries: (
            "AbstractQuery", "DataStoreQuery", "FederatedQueryResult",
            "MetadataStoreQuery", "Query", "QueryResult", "RemoteSparqlQuery",
            "SparqlQuery", "SQLQuery",
        ),
        store_manager: ("StoreManager",),
        memory: ("InMemoryRDFStore",),
        sparql: ("GraphDB", "RemoteSparqlStore"),
        sql: ("DatabaseResource", "HDF5SqlDB"),
    }
    for module, names in definitions.items():
        for name in names:
            assert getattr(core, name) is getattr(module, name)
            if name in catalog.__all__:
                assert getattr(catalog, name) is getattr(module, name)
    assert core._format_shacl_report is sparql._format_shacl_report


def test_store_manager_classifies_stores(tmp_path):
    rdf_store = catalog.InMemoryRDFStore(tmp_path / "rdf")
    data_store = catalog.HDF5FileStore(tmp_path / "hdf")
    manager = core.StoreManager({"metadata": rdf_store, "data": data_store})

    assert manager.metadata is rdf_store
    assert manager["data"] is data_store
    assert manager.metadata_stores == {"metadata": rdf_store}
    assert manager.data_stores == {"data": data_store}
    with pytest.raises(ValueError, match="already exists"):
        manager.add_store("metadata", rdf_store)


@pytest.mark.parametrize("literal", [
    rdflib.Literal("001", datatype=rdflib.XSD.integer, normalize=False),
    rdflib.Literal("Temperatur", lang="de"),
])
def test_local_queries_preserve_rdf_terms(tmp_path, literal):
    store = catalog.InMemoryRDFStore(tmp_path)
    subject = rdflib.URIRef("urn:example:sample")
    predicate = rdflib.URIRef("urn:example:value")
    store.upload_triple((subject, predicate, literal))

    selected = catalog.SparqlQuery("SELECT ?value WHERE { ?s ?p ?value }").execute(store)
    assert selected.data.iloc[0]["value"] == literal
    assert str(selected.data.iloc[0]["value"]) == str(literal)

    constructed = catalog.SparqlQuery(
        "CONSTRUCT { ?s ?p ?value } WHERE { ?s ?p ?value }"
    ).execute(store)
    assert isomorphic(constructed.derived_graph, store.graph)
    assert str(constructed.derived_graph.value(subject, predicate)) == str(literal)


@pytest.mark.parametrize("query_class", [catalog.SparqlQuery, catalog.RemoteSparqlQuery])
def test_remote_query_dispatch(monkeypatch, query_class):
    wrapper = Mock()
    wrapper.queryAndConvert.return_value = {
        "head": {"vars": ["value"]},
        "results": {"bindings": [{"value": {"type": "literal", "value": "sample"}}]},
    }
    monkeypatch.setattr("SPARQLWrapper.SPARQLWrapper", Mock(return_value=wrapper))
    store = catalog.RemoteSparqlStore("https://example.org/sparql")
    query = query_class("SELECT ?value WHERE { ?s ?p ?value }", "Sample values")

    result = query.execute(store)

    assert isinstance(result, core.QueryResult)
    assert result.query == query
    assert result.description == "Sample values"
    assert result.data["value"].tolist() == ["sample"]
    wrapper.setQuery.assert_called_once_with(query.query)
    wrapper.queryAndConvert.assert_called_once_with()


def test_remote_query_keeps_graph_response(monkeypatch):
    graph = rdflib.Graph()
    wrapper = Mock()
    wrapper.queryAndConvert.return_value = graph
    monkeypatch.setattr("SPARQLWrapper.SPARQLWrapper", Mock(return_value=wrapper))
    store = catalog.RemoteSparqlStore("https://example.org/sparql")

    result = catalog.RemoteSparqlQuery("DESCRIBE <urn:example:sample>").execute(store)

    assert result.data is graph


def test_remote_query_rejects_local_store(tmp_path):
    store = catalog.InMemoryRDFStore(tmp_path)
    with pytest.raises(TypeError, match="RemoteSparqlStore"):
        catalog.RemoteSparqlQuery("SELECT * WHERE { ?s ?p ?o }").execute(store)


def test_graphdb_reports_shacl_failure(monkeypatch):
    monkeypatch.setattr("SPARQLWrapper.SPARQLWrapper", Mock())
    monkeypatch.setattr(catalog.GraphDB, "get_repository_info", Mock(return_value={}))
    response = Mock(status_code=500, text='''
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        [] a sh:ValidationResult ;
            sh:focusNode <urn:example:sample> ;
            sh:resultPath <urn:example:age> ;
            sh:value "invalid" ;
            sh:resultSeverity sh:Violation ;
            sh:sourceConstraintComponent sh:DatatypeConstraintComponent .
    ''')
    post = Mock(return_value=response)
    monkeypatch.setattr("requests.post", post)
    store = catalog.GraphDB("https://example.org", "test")

    with pytest.raises(ValueError, match="SHACL validation failed") as error:
        store.upload_triple((
            rdflib.URIRef("urn:example:sample"),
            rdflib.URIRef("urn:example:age"),
            rdflib.Literal("invalid"),
        ))

    assert "Resource: urn:example:sample" in str(error.value)
    assert "Constraint: DatatypeConstraintComponent" in str(error.value)
    post.assert_called_once()
