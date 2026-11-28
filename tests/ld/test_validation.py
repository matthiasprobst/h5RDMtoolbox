"""SHACL contracts replacing layout rules, using ordinary h5py files."""
import json
from unittest.mock import patch

import h5py
import numpy as np
import pytest
import rdflib
from rdflib.compare import isomorphic

from h5rdmtoolbox.ld import get_ld
from h5rdmtoolbox.validation import validate

HDF = rdflib.Namespace('http://purl.allotrope.org/ontologies/hdf5/1.8#')
EX = rdflib.Namespace('https://example.org/')
PREFIX = '''
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/> .
'''


def shapes(text=''):
    return rdflib.Graph().parse(data=PREFIX + text, format='turtle')


LAYOUT = '''
ex:File a sh:NodeShape; sh:targetClass hdf:File;
  sh:property [ sh:path (hdf:rootGroup hdf:member);
    sh:qualifiedValueShape [ sh:property [ sh:path hdf:name; sh:hasValue "/u" ] ];
    sh:qualifiedMinCount 1; sh:qualifiedMaxCount 1 ].
ex:Dataset a sh:NodeShape; sh:targetClass hdf:Dataset;
  sh:property [ sh:path hdf:rank; sh:hasValue 2 ];
  sh:property [ sh:path hdf:datatype; sh:hasValue hdf:H5T_IEEE_F64LE ];
  sh:property [ sh:path (hdf:filter rdf:type); sh:hasValue hdf:FilterDeflate ];
  sh:property [ sh:path (hdf:dataspace hdf:dimension);
    sh:qualifiedValueShape [
      sh:property [ sh:path hdf:dimensionIndex; sh:hasValue 0 ];
      sh:property [ sh:path hdf:size; sh:hasValue 3 ] ];
    sh:qualifiedMinCount 1; sh:qualifiedMaxCount 1 ].
'''


@pytest.mark.parametrize('name,shape,dtype,compression,conforms', [
    ('u', (3, 5), '<f8', 'gzip', True),
    ('v', (3, 5), '<f8', 'gzip', False),
    ('u', (3,), '<f8', 'gzip', False),
    ('u', (4, 5), '<f8', 'gzip', False),
    ('u', (3, 5), '<f4', 'gzip', False),
    ('u', (3, 5), '<f8', 'lzf', False),
])
def test_layout_structure(tmp_path, name, shape, dtype, compression, conforms):
    filename = tmp_path / 'file.h5'
    with h5py.File(filename, 'w') as handle:
        handle.create_dataset(name, shape=shape, dtype=dtype, compression=compression)
    result = validate(filename, shapes(LAYOUT))
    assert result.conforms is conforms
    if not conforms:
        assert result.violations
        assert all(item.hdf_path in ('/', '/u') for item in result.violations)
        assert all(item.severity == rdflib.SH.Violation for item in result.violations)


@pytest.mark.parametrize('include_values', [False, True])
def test_value_policy_applies_to_nested_and_contextual_graphs(tmp_path, include_values):
    filename = tmp_path / 'file.h5'
    with h5py.File(filename, 'w') as handle:
        for name, data in [('scalar', 1), ('nested/scalar', 2), ('nested/array', [1, 2])]:
            ds = handle.create_dataset(name, data=data)
            ds.attrs['RDF_PREDICATE'] = json.dumps({'DATA_PREDICATE': str(EX.value)})
        handle['nested'].attrs['AUTHOR'] = 'Ada'
    reads = []
    original = h5py.Dataset.__getitem__

    def read(dataset, key, *args, **kwargs):
        reads.append(dataset.name)
        assert include_values and dataset.shape == ()
        return original(dataset, key, *args, **kwargs)

    with patch.object(h5py.Dataset, '__getitem__', read):
        graph = get_ld(filename, include_scalar_values=include_values)
        result = validate(filename, shapes(), include_scalar_values=include_values)
    assert result.conforms
    assert bool(reads) is include_values
    assert len(list(graph.triples((None, EX.value, None)))) == (2 if include_values else 0)
    assert len(list(graph.triples((None, HDF.value, None)))) == (2 if include_values else 0)
    assert (None, HDF.name, rdflib.Literal('AUTHOR')) in graph


def test_path_and_open_file_mapping_parity(tmp_path):
    filename = tmp_path / 'file.h5'
    with h5py.File(filename, 'w') as handle:
        handle.attrs['title'] = 'Measurement'
    options = dict(structural=False, contextual=True, file_uri=str(EX),
                   rdf_mappings={'title': {'predicate': str(EX.title)}})
    by_path = get_ld(filename, **options)
    with h5py.File(filename) as handle:
        assert isomorphic(by_path, get_ld(handle, **options))
        assert validate(handle, shapes()).conforms
        assert handle.id.valid
    assert (None, EX.title, rdflib.Literal('Measurement')) in by_path


def test_graph_inputs_are_not_modified_and_ontology_is_explicit():
    graph = shapes('ex:item a ex:Specific .')
    ontology = shapes('ex:Specific <http://www.w3.org/2000/01/rdf-schema#subClassOf> ex:General .')
    rules = shapes('ex:S a sh:NodeShape; sh:targetNode ex:item; sh:class ex:General .')
    snapshots = [set(g) for g in (graph, ontology, rules)]
    assert not validate(graph, rules).conforms
    assert validate(graph, rules, ontology=ontology, inference='rdfs').conforms
    assert [set(g) for g in (graph, ontology, rules)] == snapshots
    with pytest.raises(ValueError, match='In-place'):
        validate(graph, rules, inplace=True)


def test_shapes_file_and_invalid_inputs(tmp_path):
    filename = tmp_path / 'shapes.ttl'
    shapes().serialize(filename, format='turtle')
    assert validate(rdflib.Graph(), filename).conforms
    with pytest.raises(FileNotFoundError):
        validate(rdflib.Graph(), tmp_path / 'missing.ttl')
    with pytest.raises(TypeError):
        validate(object(), shapes())
    filename.write_text('not valid Turtle {', encoding='utf-8')
    with pytest.raises(Exception):
        validate(rdflib.Graph(), filename)


@pytest.mark.parametrize('names,valid', [(['u'], True), (['v'], True), (['w'], False)])
def test_alternative_required_paths(tmp_path, names, valid):
    filename = tmp_path / 'file.h5'
    with h5py.File(filename, 'w') as handle:
        for name in names:
            handle.create_dataset(name, data=1)
    rules = shapes('''ex:S a sh:NodeShape; sh:targetClass hdf:File;
      sh:property [ sh:path (hdf:rootGroup hdf:member);
        sh:qualifiedValueShape [ sh:property [ sh:path hdf:name; sh:in ("/u" "/v") ] ];
        sh:qualifiedMinCount 1 ].''')
    assert validate(filename, rules).conforms is valid


@pytest.mark.parametrize('steady,with_time,valid', [(False, False, True), (True, False, False), (True, True, True)])
def test_conditional_root_requirement(tmp_path, steady, with_time, valid):
    filename = tmp_path / 'file.h5'
    with h5py.File(filename, 'w') as handle:
        handle.create_group('setup').attrs['standard_name'] = 'Steady State' if steady else 'Other'
        if with_time:
            handle.create_dataset('TIME', data=[1, 2])
    rules = shapes('''ex:S a sh:NodeShape; sh:targetClass hdf:File;
      sh:sparql [ sh:message "Steady State requires TIME";
        sh:select """SELECT $this WHERE {
          $this hdf:rootGroup ?root .
          ?root hdf:member/hdf:attribute ?attribute .
          ?attribute hdf:name "standard_name"; hdf:data "Steady State" .
          FILTER NOT EXISTS { ?root hdf:member ?time . ?time hdf:name "/TIME" . }
        }""" ].''')
    assert validate(filename, rules).conforms is valid
