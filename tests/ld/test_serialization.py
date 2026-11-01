"""Cross-entry-point contracts for RDF serialization without remote resources."""

import json

import pytest
import rdflib
from rdflib.compare import isomorphic

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.ld import get_ld, hdf2jsonld, hdf2ttl


@pytest.mark.parametrize("structural,contextual", [(True, True), (True, False), (False, True)])
@pytest.mark.parametrize("fmt", ["ttl", "json-ld"])
def test_serialization_entry_points_preserve_graph(tmp_path, structural, contextual, fmt):
    filename = tmp_path / "measurement.hdf"
    predicate = rdflib.URIRef("https://example.org/vocab/description")
    with h5tbx.File(filename, "w") as h5:
        dataset = h5.create_dataset("temperature", data=[20, 21])
        dataset.attrs["description", predicate] = "Room temperature"

    options = dict(structural=structural, contextual=contextual, file_uri="https://example.org/data#")
    context = {"measurement": "https://example.org/vocab/"}
    expected = get_ld(filename, **options)
    with h5tbx.File(filename) as h5:
        outputs = [h5.serialize(fmt, context=context, **options)]
        if fmt == "json-ld":
            outputs.append(h5.dump_jsonld(context=context, **options))
    outputs.append(h5tbx.serialize(filename, fmt=fmt, **options))
    export = hdf2ttl if fmt == "ttl" else hdf2jsonld
    outputs.append(export(filename, context=context, **options).read_text(encoding="utf-8"))
    if fmt == "json-ld":
        outputs.append(h5tbx.dump_jsonld(filename, context=context, **options))
        assert json.loads(outputs[0])["@context"]["measurement"] == context["measurement"]
    for output in outputs:
        assert isomorphic(expected, rdflib.Graph().parse(data=output, format=fmt))
    assert context == {"measurement": "https://example.org/vocab/"}


def test_jsonld_entry_points_keep_distinct_uri_validation(tmp_h5_file):
    uri = "https://example.org/data/"
    with pytest.raises(ValueError, match="must end with '#'"):
        tmp_h5_file.dump_jsonld(file_uri=uri)
    assert h5tbx.dump_jsonld(tmp_h5_file.hdf_filename, file_uri=uri)
