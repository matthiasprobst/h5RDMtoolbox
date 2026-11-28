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


def test_validation_example(quickstart):
    namespace = {}
    exec(compile(PYTHON_EXAMPLES[1], 'README validation', 'exec'), namespace)
    assert namespace['result'].conforms


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
