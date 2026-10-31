"""Characterize the on-disk RDF contract independently of the RDF getters."""

import json

import h5py
import numpy as np
import pytest
import rdflib
from ontolutils import Thing

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.ld.rdf import RDFError, append, set_object, set_predicate


BASE = 'https://example.org/'


def assert_raw_text(obj, name, expected):
    """Inspect h5py values and HDF5 string metadata, bypassing wrapper parsing."""
    attrs = h5py.AttributeManager(obj)
    assert attrs[name] == expected
    attribute_id = attrs.get_id(name)
    assert attribute_id.shape == ()
    string_type = h5py.check_string_dtype(attribute_id.dtype)
    assert string_type.encoding == 'utf-8'
    assert string_type.length is None


def assert_raw_mapping(obj, name, expected):
    assert_raw_text(obj, name, json.dumps(expected))


@pytest.fixture(params=['root', 'group', 'dataset'])
def target(tmp_h5_file, request):
    if request.param == 'group':
        return tmp_h5_file.create_group('group')
    if request.param == 'dataset':
        return tmp_h5_file.create_dataset('dataset', data=[1, 2])
    return tmp_h5_file


def test_mapping_write_sequence(target):
    target.attrs['label'] = 'café'
    target.attrs['other'] = 'untouched'
    target.rdf.predicate['other'] = BASE + 'other'
    target.rdf['label'].predicate = BASE + 'has label'
    # Predicate assignment validates without normalizing; objects normalize URLs.
    assert_raw_mapping(target, 'RDF_PREDICATE', {
        'other': BASE + 'other', 'label': BASE + 'has label',
    })
    target.rdf.object['label'] = BASE + 'first object'
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': BASE + 'first%20object'})
    target.rdf.object['label'] = (BASE + 'second', BASE + 'second')
    target.rdf['label'].append_object([BASE + 'third', BASE + 'fourth'])
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': [
        BASE + 'first%20object', BASE + 'second', BASE + 'second',
        BASE + 'third', BASE + 'fourth',
    ]})
    target.rdf['label'].definition = 'Définition'
    assert_raw_mapping(target, 'ATTR_DEFINITION', {'label': 'Définition'})
    del target.rdf.predicate['label']
    del target.rdf.object['label']
    assert_raw_mapping(target, 'RDF_PREDICATE', {'other': BASE + 'other'})
    assert_raw_text(target, 'RDF_OBJECT', '{}')
    assert_raw_text(target, 'label', 'café')


@pytest.mark.parametrize('factory,expected', [
    (lambda: rdflib.BNode('object'), '_:object'),
    (lambda: rdflib.Literal('bonjour', lang='fr'), {
        'lexical_or_value': 'bonjour', 'lang': 'fr', '$type': 'rdflib.term.Literal',
    }),
    (lambda: rdflib.Literal(7), '7'),
    (lambda: {'@context': {'ex': BASE}, '@graph': [
        {'@id': BASE + 'object', '@type': 'ex:Thing'},
    ]}, {'@context': {'ex': BASE}, '@id': BASE + 'object', '@type': 'ex:Thing'}),
])
def test_object_encoding(target, factory, expected):
    target.attrs['label'] = 'value'
    target.rdf.object['label'] = factory()
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': expected})


def test_thing_encoding(target):
    thing = Thing(id=BASE + 'object')
    expected = thing.get_jsonld_dict()
    target.attrs['label'] = 'value'
    target.rdf.object['label'] = thing
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': expected})


def test_empty_sequences_and_missing_mapping_deletion(target):
    target.attrs['label'] = 'value'
    target.rdf.object['label'] = []
    assert 'RDF_OBJECT' not in target.attrs.raw
    with pytest.raises(IndexError):
        target.rdf['label'].object = []
    del target.rdf.object['label']
    assert_raw_text(target, 'RDF_OBJECT', '{}')


def test_json_string_entry_point(target):
    target.attrs['label'] = 'value'
    data = {'@type': BASE + 'Thing', '@id': BASE + 'object'}
    target.rdf['label'].object = json.dumps(data)
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': data})


@pytest.mark.parametrize('invalid', [
    {'@graph': [{'@type': BASE + 'A'}, {'@type': BASE + 'B'}]},
    {'@id': BASE + 'object'},
    'invalid object',
])
def test_rejected_objects_do_not_overwrite_existing_mapping(target, invalid):
    target.attrs['label'] = 'value'
    target.rdf.object['label'] = BASE + 'object'
    with pytest.raises(RDFError):
        target.rdf.object['label'] = invalid
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': BASE + 'object'})


def test_entry_points_preserve_their_write_semantics(target):
    target.attrs['label', BASE + 'label'] = h5tbx.Attribute('value', rdf_object=BASE + 'object')
    target.attrs.create('other', 'other value', rdf_predicate=BASE + 'other', definition='definition')
    assert_raw_mapping(target, 'RDF_PREDICATE', {'label': BASE + 'label', 'other': BASE + 'other'})
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': BASE + 'object'})
    assert_raw_mapping(target, 'ATTR_DEFINITION', {'other': 'definition'})
    # The IRIDict sequence path validates its first element and appends the rest as-is.
    target.rdf['label'].object = [BASE + 'first', 'unvalidated tail']
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': [BASE + 'object', BASE + 'first', 'unvalidated tail']})


def test_invalid_sequence_retains_prior_writes(target):
    target.attrs['label'] = 'value'
    with pytest.raises(RDFError):
        target.rdf.object['label'] = [BASE + 'first', 'invalid object']
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': BASE + 'first'})
    with pytest.raises(KeyError):
        append(target.attrs, 'missing', BASE + 'object', 'RDF_OBJECT')
    assert_raw_mapping(target, 'RDF_OBJECT', {'label': BASE + 'first'})


def test_file_scope_storage_and_legacy_predicate_routing(tmp_h5_file):
    h5 = tmp_h5_file
    h5.attrs['label'] = 'value'
    h5.frdf['label'].predicate = BASE + 'fileLabel'
    h5.frdf['label'].object = [BASE + 'first', BASE + 'second']
    assert_raw_mapping(h5, 'RDF_FILE_PREDICATE', {'label': BASE + 'fileLabel'})
    assert_raw_mapping(h5, 'RDF_FILE_OBJECT', {'label': [BASE + 'first', BASE + 'second']})
    # Preserve the existing separate mapping-assignment route in this refactor.
    h5.frdf.predicate['label'] = BASE + 'legacyRoute'
    assert_raw_mapping(h5, 'RDF_PREDICATE', {'label': BASE + 'legacyRoute'})
    assert_raw_mapping(h5, 'RDF_FILE_PREDICATE', {'label': BASE + 'fileLabel'})
    del h5.frdf['label'].object
    assert_raw_text(h5, 'RDF_FILE_OBJECT', '{}')


@pytest.mark.parametrize('scope,prefix', [('rdf', 'RDF_'), ('frdf', 'RDF_FILE_')])
def test_type_and_subject_representation(tmp_h5_file, scope, prefix):
    manager = getattr(tmp_h5_file, scope)
    manager.subject = BASE + 'a subject'
    assert_raw_text(tmp_h5_file, prefix + 'ID', BASE + 'a%20subject')
    manager.type = BASE + 'Type'
    assert_raw_text(tmp_h5_file, prefix + 'TYPE', BASE + 'Type')
    manager.type = BASE + 'Type'
    raw = h5py.AttributeManager(tmp_h5_file)
    np.testing.assert_array_equal(raw[prefix + 'TYPE'], [BASE + 'Type'])
    assert raw.get_id(prefix + 'TYPE').shape == (1,)
    with pytest.raises(RDFError):
        manager.type = [BASE + 'OtherType', 'invalid']
    np.testing.assert_array_equal(raw[prefix + 'TYPE'], [BASE + 'Type'])


def test_legacy_type_and_raw_json_object_mapping(tmp_h5_file):
    tmp_h5_file.attrs['@TYPE'] = BASE + 'Type'
    with pytest.warns(DeprecationWarning):
        tmp_h5_file.rdf.type = BASE + 'Type'
    np.testing.assert_array_equal(tmp_h5_file.attrs.raw['RDF_TYPE'], [BASE + 'Type'])
    assert_raw_text(tmp_h5_file, '@TYPE', BASE + 'Type')
    # A minimal attribute backend can return serialized mappings instead of dicts.
    attrs = {'RDF_OBJECT': '{"other": "https://example.org/other"}'}
    set_object(attrs, 'label', BASE + 'object')
    assert attrs['RDF_OBJECT'] == {'other': BASE + 'other', 'label': BASE + 'object'}


def test_reopened_file_contains_original_rdf_attributes(tmp_path):
    filename = tmp_path / 'rdf.h5'
    with h5tbx.File(filename, 'w') as h5:
        group = h5.create_group('group')
        group.attrs['label', BASE + 'label'] = 'value'
        group.rdf['label'].object = rdflib.BNode('fixed')
        h5.frdf.subject = BASE + 'file'
    with h5py.File(filename, 'r') as raw:
        assert_raw_mapping(raw['group'], 'RDF_PREDICATE', {'label': BASE + 'label'})
        assert_raw_mapping(raw['group'], 'RDF_OBJECT', {'label': '_:fixed'})
        assert_raw_text(raw, 'RDF_FILE_ID', BASE + 'file')


def test_predicate_blank_node_and_custom_storage_name(target):
    set_predicate(target.attrs, 'label', rdflib.BNode('fixed'), rdf_predicate_attr_name='CUSTOM')
    assert_raw_mapping(target, 'CUSTOM', {'label': '_:fixed'})
