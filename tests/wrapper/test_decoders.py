"""Check scale/offset values and the boundary between storage and decoded data."""

import numpy as np
import pytest
import xarray as xr

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.wrapper.ds_decoder import scale_and_offset_decoder


@pytest.mark.parametrize('with_scale,with_offset', [
    (False, False), (True, False), (False, True), (True, True),
])
@pytest.mark.parametrize('reference_kind', ['path', 'dataset'])
def test_decoder_removes_storage_markers(tmp_h5_file, with_scale, with_offset, reference_kind):
    with h5tbx.use('h5tbx'):
        scale = tmp_h5_file.create_dataset('scale', data=2., attrs={'units': ''})
        offset = tmp_h5_file.create_dataset('offset', data=3., attrs={'units': 'm'})
        dataset = tmp_h5_file.create_dataset('signal', data=[1., 2.], attrs={'units': 'm'})
        attrs = {'units': 'm', 'IS_DATA_SCALE': True, 'IS_DATA_OFFSET': True}
        if with_scale:
            attrs['DATA_SCALE'] = scale.name if reference_kind == 'path' else scale
        if with_offset:
            attrs['DATA_OFFSET'] = offset.name if reference_kind == 'path' else offset
        source = xr.DataArray([1., 2.], dims=['sample'], coords={'sample': [10, 20]}, attrs=attrs)

        result = scale_and_offset_decoder(source, dataset)

        expected = np.array([1., 2.]) * (2 if with_scale else 1) + (3 if with_offset else 0)
        np.testing.assert_allclose(result.values, expected)
        assert h5tbx.get_ureg().Unit(result.attrs['units']) == h5tbx.get_ureg().Unit('m')
        np.testing.assert_array_equal(result.coords['sample'], [10, 20])
        assert not {'DATA_SCALE', 'DATA_OFFSET', 'IS_DATA_SCALE', 'IS_DATA_OFFSET'} & result.attrs.keys()


def test_decoded_read_preserves_stored_calibration(tmp_h5_file):
    with h5tbx.use('h5tbx'):
        scale = tmp_h5_file.create_dataset('scale', data=2., attrs={'units': ''})
        offset = tmp_h5_file.create_dataset('offset', data=3., attrs={'units': 'm'})
        dataset = tmp_h5_file.create_dataset('signal', data=[1., 2.], attrs={'units': 'm'})
        dataset.attach_data_scale_and_offset(scale, offset)
        scale.attrs['IS_DATA_SCALE'] = True
        offset.attrs['IS_DATA_OFFSET'] = True

        np.testing.assert_allclose(dataset[()].values, [5., 7.])
        np.testing.assert_allclose(dataset.values[()], [1., 2.])
        assert dataset.attrs['DATA_SCALE'] == scale.name
        assert dataset.attrs['DATA_OFFSET'] == offset.name
        assert 'IS_DATA_SCALE' not in scale[()].attrs
        assert 'IS_DATA_OFFSET' not in offset[()].attrs
        assert bool(scale.attrs['IS_DATA_SCALE'])
        assert bool(offset.attrs['IS_DATA_OFFSET'])
