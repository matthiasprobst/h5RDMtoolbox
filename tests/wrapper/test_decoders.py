"""Check scale/offset values and the boundary between storage and decoded data."""

import numpy as np
import pytest
import xarray as xr

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.science.calibration import scale_and_offset_decoder


@pytest.mark.parametrize('with_scale,with_offset', [
    (False, False), (True, False), (False, True), (True, True),
])
@pytest.mark.parametrize('reference_kind', ['path', 'dataset'])
def test_decoder_removes_storage_markers(tmp_h5_file, with_scale, with_offset, reference_kind):
    with h5tbx.File(tmp_h5_file.id, decode_calibration=True) as tmp_h5_file:
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
    with h5tbx.File(tmp_h5_file.id, decode_calibration=True) as tmp_h5_file:
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


def test_calibration_is_per_open_file_and_propagates(tmp_path):
    filename = tmp_path / "calibrated.h5"
    with h5tbx.File(filename, "w") as file:
        group = file.create_group("nested")
        scale = group.create_dataset("scale", data=2., attrs={"units": ""})
        offset = group.create_dataset("offset", data=3., attrs={"units": "m"})
        signal = group.create_dataset("signal", data=[1., 2.], attrs={"units": "m"})
        signal.attach_data_scale_and_offset(scale, offset)
    with h5tbx.File(filename) as raw, h5tbx.File(filename, decode_calibration=True) as decoded:
        assert not raw.decode_calibration
        assert decoded.decode_calibration
        for obj in (decoded["nested/signal"], decoded["nested"]["signal"],
                    decoded["nested/signal"].parent["signal"],
                    decoded["nested"].rootparent["nested/signal"]):
            assert obj.decode_calibration
            np.testing.assert_allclose(obj[()].values, [5., 7.])
            np.testing.assert_allclose(obj.values[()], [1., 2.])
        np.testing.assert_allclose(raw["nested/signal"][()].values, [1., 2.])
        assert decoded["nested/signal"].attrs["DATA_SCALE"] == "/nested/scale"


def test_invalid_calibration_fails_only_on_decoded_read(tmp_path):
    filename = tmp_path / "bad-calibration.h5"
    with h5tbx.File(filename, "w") as file:
        file.create_dataset("signal", data=[1., 2.], attrs={"units": "m", "DATA_SCALE": "/missing"})
    with h5tbx.File(filename) as file:
        np.testing.assert_allclose(file["signal"][()].values, [1., 2.])
    with h5tbx.File(filename, decode_calibration=True) as file:
        with pytest.raises(ValueError, match="Cannot decode calibration"):
            file["signal"][()]
        np.testing.assert_allclose(file["signal"].values[()], [1., 2.])


def test_invalid_calibration_option(tmp_path):
    with pytest.raises(TypeError, match="decode_calibration"):
        h5tbx.File(tmp_path / "unused.h5", "w", decode_calibration="yes")
