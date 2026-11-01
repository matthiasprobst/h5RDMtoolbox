"""Preserve quantity-text round trips independently of Pint parser versions."""

import pytest

import h5rdmtoolbox as h5tbx


@pytest.mark.parametrize('scope', ['file', 'group', 'dataset'])
@pytest.mark.parametrize('text,magnitude,unit', [
    ('1.2 [m]', 1.2, 'm'),
    ('1.2[m/s]', 1.2, 'm/s'),
    ('1.2 [m] / [s]', 1.2, 'm/s'),
    ('1.2 [m**2]', 1.2, 'm**2'),
    ('1.2 (m)', 1.2, 'm'),
    ('1.2m', 1.2, 'm'),
    ('-1.2e3 [m]', -1200, 'm'),
])
def test_quantity_conversion_preserves_stored_text(tmp_h5_file, scope, text, magnitude, unit):
    objects = {
        'file': tmp_h5_file,
        'group': tmp_h5_file.create_group('group'),
        'dataset': tmp_h5_file.create_dataset('data', data=[1, 2]),
    }
    obj = objects[scope]
    obj.attrs['measurement'] = text
    quantity = obj.attrs['measurement'].to_pint()
    expected = h5tbx.get_ureg().Quantity(magnitude, unit)
    assert quantity.units == expected.units
    assert quantity.magnitude == pytest.approx(magnitude)
    assert (quantity + 0 * expected).magnitude == pytest.approx(magnitude)
    assert str(obj.attrs['measurement']) == text
