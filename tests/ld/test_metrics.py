import rdflib

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.ld.metrics import compute_graph_metrics, graph_label


def test_compute_metrics_from_filename():
    with h5tbx.File() as h5:
        h5.create_group("grp")
        filename = h5.hdf_filename

    metrics = h5tbx.compute_metrics(filename)

    assert metrics["triples"] > 0
    assert metrics["subjects"] > 0
    assert metrics["predicates"] > 0
    assert metrics["classes"] > 0
    assert metrics["largest_distance"] >= 0
    assert ("hdf:File", 1) in metrics["top_classes"]
    assert any(label == "hdf:rootGroup" for label, _ in metrics["top_predicates"])


def test_file_metrics_method():
    with h5tbx.File() as h5:
        h5.create_group("grp")

        metrics = h5.metrics()

    assert metrics["triples"] > 0
    assert metrics["resource_nodes"] > 0
    assert metrics["components"] >= 1
    assert metrics["largest_component"] >= 1


def test_compute_graph_metrics_for_existing_graph():
    graph = rdflib.Graph()
    graph.add((rdflib.URIRef("https://example.org/a"), rdflib.RDF.type, rdflib.URIRef("https://example.org/Class")))
    graph.add((rdflib.URIRef("https://example.org/a"), rdflib.RDFS.label, rdflib.Literal("A")))
    graph.add((rdflib.URIRef("https://example.org/a"), rdflib.URIRef("https://example.org/linksTo"), rdflib.URIRef("https://example.org/b")))

    metrics = compute_graph_metrics(graph, base_namespace="https://example.org/")

    assert metrics["triples"] == 3
    assert metrics["subjects"] == 1
    assert metrics["objects"] == 3
    assert metrics["subjects_with_labels"] == 1
    assert metrics["label_coverage"] == 100.0
    assert metrics["largest_distance"] == 2
    assert metrics["largest_distance_computed"] is True


def test_compute_graph_metrics_skips_largest_distance_above_limit():
    graph = rdflib.Graph()
    for index in range(4):
        graph.add((
            rdflib.URIRef(f"https://example.org/{index}"),
            rdflib.URIRef("https://example.org/linksTo"),
            rdflib.URIRef(f"https://example.org/{index + 1}"),
        ))

    metrics = compute_graph_metrics(graph, distance_node_limit=3)

    assert metrics["resource_nodes"] == 5
    assert metrics["largest_distance"] is None
    assert metrics["largest_distance_computed"] is False
    assert metrics["largest_distance_node_limit"] == 3


def test_graph_label_uses_short_zenodo_prefixes():
    assert graph_label(
        rdflib.URIRef("https://doi.org/10.5281/zenodo.18349039#2023-11-07/adalwjdawd@quantitykind")
    ) == "zen:18349039#2023-11-07/adalwjdawd@quantitykind"
    assert graph_label(
        rdflib.URIRef("https://zenodo.org/records/18349039#2023-11-07/adalwjdawd@quantitykind")
    ) == "rzen:18349039#2023-11-07/adalwjdawd@quantitykind"
    assert graph_label(
        rdflib.URIRef("https://zenodo.org/record/18349039/files/data.h5")
    ) == "rzen:18349039/files/data.h5"


def test_graph_label_keeps_non_zenodo_doi_prefix():
    assert graph_label(rdflib.URIRef("https://doi.org/10.1234/example")) == "doi:10.1234/example"
