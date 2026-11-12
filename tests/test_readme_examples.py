"""Execute the README's actual Python snippets and compare its RDF examples."""

from pathlib import Path
import re
import shlex

import h5py
import pytest
import rdflib
from rdflib.compare import isomorphic
from typer.testing import CliRunner

from h5rdmtoolbox_cli import h5tbx


README = (Path(__file__).parents[1] / 'README.md').read_text(encoding='utf-8')
PYTHON_EXAMPLES = re.findall(r'```python\n(.*?)```', README, re.S)


@pytest.fixture
def quickstart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    namespace = {}
    exec(compile(PYTHON_EXAMPLES[0], 'README quickstart', 'exec'), namespace)
    return namespace


def test_quickstart_measurements(quickstart):
    with h5py.File('example.h5') as handle:
        assert handle['temperature'][:].tolist() == [20, 21, 19, 22]
        assert handle['temperature'].dtype.itemsize == 8
        assert handle['mean_temperature'][()] == 20.5


@pytest.mark.parametrize('index', [0, 1])
def test_displayed_turtle_matches_generated_graph(quickstart, index):
    examples = re.findall(r'```ttl\n(.*?)```', README, re.S)
    expected = rdflib.Graph().parse(data=examples[index], format='turtle')
    actual = rdflib.Graph().parse(data=quickstart[('ttl_ctx', 'ttl_struc')[index]], format='turtle')
    assert isomorphic(actual, expected)


@pytest.mark.parametrize('index', [1, 2, 3])
def test_other_python_examples_have_independent_imports(quickstart, index):
    # The metrics example consumes example.h5, but every block imports its own APIs.
    namespace = {}
    exec(compile(PYTHON_EXAMPLES[index], f'README Python example {index + 1}', 'exec'), namespace)
    if index == 1:
        assert namespace['metrics']['triples'] > 0
    elif index == 2:
        with namespace['h5tbx'].File('experiment.h5') as handle:
            graph = rdflib.Graph().parse(data=handle.serialize(
                'ttl', structural=False, contextual=True,
                file_uri='https://example.org/experiment/'), format='turtle')
        values = list(graph.objects(predicate=rdflib.URIRef('http://purl.org/dc/terms/created')))
        assert len(values) == 1
        assert values[0].datatype == rdflib.XSD.date
        assert str(values[0]) == '2025-01-10'
    else:
        with h5py.File('uncompressed.h5') as handle:
            assert handle['data'].compression is None


@pytest.mark.parametrize('write_file', [False, True])
def test_cli_dump_examples(quickstart, write_file):
    if write_file:
        command, = re.findall(r'^h5tbx ld dump example.h5 -o example.jsonld$', README, re.M)
    else:
        command, = re.findall(r'`(h5tbx ld dump example.h5)`', README)
    result = CliRunner().invoke(h5tbx, shlex.split(command)[1:])
    assert result.exit_code == 0, result.output
    if write_file:
        graph = rdflib.Graph().parse('example.jsonld', format='json-ld')
    else:
        graph = rdflib.Graph().parse(data=result.stdout, format='turtle')
    values = list(graph.objects(predicate=rdflib.URIRef(
        'http://w3id.org/nfdi4ing/metadata4ing#hasNumericalValue')))
    assert len(values) == 1
    assert float(values[0]) == 20.5
