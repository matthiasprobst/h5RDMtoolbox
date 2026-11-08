"""Contextual RDF preserves lexical metadata instead of guessing dates."""

import pytest
import h5rdmtoolbox as h5tbx
from rdflib import Literal, URIRef, XSD


@pytest.mark.parametrize('kind', ['file', 'root', 'group', 'dataset'])
@pytest.mark.parametrize('value', [
    '3', '00123', '1.2.3', '2025', '2025-01-10',
    '2025-01-10T01:02:03Z', '31/12/2025', 'not a date',
])
def test_contextual_strings_remain_strings(tmp_path, kind, value):
    filename = tmp_path / 'metadata.h5'
    predicate = URIRef('https://example.org/value')
    with h5tbx.File(filename, 'w') as handle:
        obj = (handle.create_group('group') if kind == 'group'
               else handle.create_dataset('data', data=[1]) if kind == 'dataset' else handle)
        obj.attrs['value'] = value
        manager = obj.frdf if kind == 'file' else obj.rdf
        manager['value'].predicate = str(predicate)
    graph = h5tbx.get_ld(filename, structural=False, contextual=True)
    assert set(graph.objects(None, predicate)) == {Literal(value)}


@pytest.mark.parametrize('kind', ['file', 'root', 'group', 'dataset'])
def test_explicit_dates_keep_declared_datatype(tmp_path, kind):
    filename = tmp_path / 'typed.h5'
    predicate = URIRef('https://example.org/created')
    expected = Literal('2025-01-10', datatype=XSD.date)
    with h5tbx.File(filename, 'w') as handle:
        obj = (handle.create_group('group') if kind == 'group'
               else handle.create_dataset('data', data=[1]) if kind == 'dataset' else handle)
        obj.attrs['created'] = '2025-01-10'
        manager = obj.frdf if kind == 'file' else obj.rdf
        manager['created'].predicate = str(predicate)
        manager['created'].object = expected
    graph = h5tbx.get_ld(filename, structural=False, contextual=True)
    assert set(graph.objects(None, predicate)) == {expected}
