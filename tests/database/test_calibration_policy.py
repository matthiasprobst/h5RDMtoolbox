"""Lazy handles retain the scientific read policy of their originating file."""

import numpy as np
import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.database.lazy import lazy


def test_lazy_calibration_is_file_local(tmp_path):
    filename = tmp_path / "calibration.h5"
    with h5tbx.File(filename, "w") as h5:
        scale = h5.create_dataset("scale", data=2., attrs={"units": ""})
        offset = h5.create_dataset("offset", data=3., attrs={"units": "m"})
        signal = h5.create_dataset("signal", data=[1., 2.], attrs={"units": "m"})
        signal.attach_data_scale_and_offset(scale, offset)
    with h5tbx.File(filename, decode_calibration=True) as calibrated:
        with h5tbx.File(filename) as stored:
            decoded_handle = lazy(calibrated["signal"])
            stored_handle = lazy(stored["signal"])
    np.testing.assert_allclose(decoded_handle[()].values, [5., 7.])
    np.testing.assert_allclose(stored_handle[()].values, [1., 2.])
    with decoded_handle as signal:
        np.testing.assert_allclose(signal[()].values, [5., 7.])
        np.testing.assert_allclose(signal.values[()], [1., 2.])
