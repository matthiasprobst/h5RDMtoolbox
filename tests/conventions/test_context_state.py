"""Local convention-context contracts without connectivity probes."""

from contextlib import ExitStack
import inspect

from pydantic import BaseModel
import pytest
import requests

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.convention import StandardAttribute
from h5rdmtoolbox.wrapper import ds_decoder


class StringValue(BaseModel):
    value: str


@pytest.fixture
def conventions(monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError('Convention state tests must not use the network')
    monkeypatch.setattr(requests.sessions.Session, 'request', reject_network)
    registry = h5tbx.convention.get_registered_conventions()
    original_registry = registry.copy()
    original_decoders = ds_decoder.registered_dataset_decoders.copy()
    original = h5tbx.convention.get_current_convention()
    result = []
    try:
        for name, factor in [('context_a', 2), ('context_b', 3)]:
            def decoder(array, dataset, multiplier=factor):
                return array * multiplier
            h5tbx.register_dataset_decoder(decoder, decoder_name=name)
            cv = h5tbx.Convention(name=name, contact=h5tbx.__author_orcid__, decoders=[name])
            cv.add_standard_attribute(StandardAttribute(
                name=name, validator=StringValue, target_method='create_dataset',
                description='Optional test label', default_value='$NONE',
            ))
            cv.register()
            result.append(cv)
        yield original, *result
    finally:
        h5tbx.use(None)
        registry.clear()
        registry.update(original_registry)
        ds_decoder.registered_dataset_decoders.clear()
        ds_decoder.registered_dataset_decoders.update(original_decoders)
        h5tbx.use(original)


def assert_state(convention, factor):
    assert h5tbx.convention.get_current_convention() is convention
    parameters = inspect.signature(h5tbx.Group.create_dataset).parameters
    for name in ('context_a', 'context_b'):
        assert (name in parameters) == (convention.name == name)
    with h5tbx.File() as handle:
        values = handle.create_dataset('data', data=[1, 2])[()].values.tolist()
    assert values == [factor, 2 * factor]


@pytest.mark.parametrize('depth', [2, 3])
def test_same_instance_nesting_restores_signatures_and_decoding(conventions, depth):
    original, cv, _ = conventions
    with ExitStack() as stack:
        for _ in range(depth):
            assert stack.enter_context(cv) is cv
            assert_state(cv, 2)
    assert_state(original, 1)


def test_distinct_and_repeated_contexts_restore_each_level(conventions):
    original, first, second = conventions
    with first:
        with second:
            with first:
                assert_state(first, 2)
            assert_state(second, 3)
        assert_state(first, 2)
    assert_state(original, 1)
    with first as entered:
        assert entered is first
        assert_state(first, 2)
    assert_state(original, 1)


def test_exception_in_same_instance_nesting_restores_outer_context(conventions):
    original, cv, _ = conventions
    with cv:
        with pytest.raises(ValueError, match='inner body'):
            with cv:
                raise ValueError('inner body')
        assert_state(cv, 2)
    assert_state(original, 1)


def test_exception_through_distinct_contexts_restores_original(conventions):
    original, first, second = conventions
    with pytest.raises(ValueError, match='body'):
        with first, second:
            raise ValueError('body')
    assert_state(original, 1)


def test_use_constructor_still_activates_immediately(conventions):
    original, cv, _ = conventions
    manager = h5tbx.use(cv)
    assert_state(cv, 2)
    with manager as entered:
        assert entered is cv
    assert_state(original, 1)


def test_failed_entry_does_not_overwrite_outer_restoration(conventions, monkeypatch):
    original, cv, _ = conventions

    def fail_activation(convention):
        raise ValueError('activation rejected')

    with cv:
        with monkeypatch.context() as patch:
            patch.setattr('h5rdmtoolbox.convention.core.use', fail_activation)
            with pytest.raises(ValueError, match='activation rejected'):
                with cv:
                    pytest.fail('Entry must fail')
        assert_state(cv, 2)
    assert_state(original, 1)
