"""Fresh-process checks for deferred features and initialization contracts."""

import os
import subprocess
import sys
import textwrap


def test_deferred_features_work_on_first_use(tmp_path):
    env = os.environ.copy()
    for variable, folder in (
        ("H5RDMTOOLBOX_USER_DATA_DIR", "data"),
        ("H5RDMTOOLBOX_CACHE_DIR", "cache"),
        ("H5RDMTOOLBOX_LOG_DIR", "log"),
    ):
        env[variable] = str(tmp_path / folder)
    script = textwrap.dedent('''
        import sys
        import h5rdmtoolbox_cli
        assert 'h5rdmtoolbox' not in sys.modules
        import h5rdmtoolbox as h5tbx
        import pint_xarray
        assert 'pyshacl' not in sys.modules
        assert 'IPython' not in sys.modules
        registry = h5tbx.get_ureg()
        assert pint_xarray.unit_registry is registry
        assert h5tbx.convention.get_current_convention().name == 'h5py'

        shapes = '@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ex: <https://example.org/> . ex:Shape a sh:NodeShape; sh:targetNode ex:item; sh:class ex:Measurement .'
        result = h5tbx.validate_hdf(
            hdf_data='@prefix ex: <https://example.org/> . ex:item ex:label "sample" .',
            shacl_data=shapes,
        )
        assert not result.conforms
        assert 'pyshacl' in sys.modules
        result = h5tbx.validate_hdf(
            hdf_data='@prefix ex: <https://example.org/> . ex:item a ex:Measurement .',
            shacl_data=shapes,
        )
        assert result.conforms

        from unittest.mock import patch
        from IPython.display import HTML
        with h5tbx.File() as h5:
            ds = h5.create_dataset('temperature', data=[20, 21])
            assert ds[()].values.tolist() == [20, 21]
            with patch('IPython.display.display') as display:
                h5.dump()
                display.assert_called_once()
                assert isinstance(display.call_args.args[0], HTML)
        assert h5tbx.get_ureg() is registry
        assert pint_xarray.unit_registry is registry
    ''')
    result = subprocess.run(
        [sys.executable, "-c", script], env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
