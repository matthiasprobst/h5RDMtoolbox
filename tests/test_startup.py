"""Import must not initialize optional engines or touch user directories."""
import os
import subprocess
import sys


def test_plain_import_has_no_side_effects(tmp_path):
    env = os.environ.copy()
    for name in ('USER_DATA_DIR', 'CACHE_DIR', 'LOG_DIR'):
        env['H5RDMTOOLBOX_' + name] = str(tmp_path / name)
    script = """
import sys
from pathlib import Path
import os
import h5rdmtoolbox
for module in ('h5py', 'xarray', 'pint', 'rdflib', 'pyshacl', 'IPython', 'requests'):
    assert module not in sys.modules, module
for name in ('USER_DATA_DIR', 'CACHE_DIR', 'LOG_DIR'):
    assert not Path(os.environ['H5RDMTOOLBOX_' + name]).exists()
"""
    result = subprocess.run([sys.executable, '-c', script], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_first_scientific_use(tmp_h5_file):
    import h5rdmtoolbox as h
    dataset = tmp_h5_file.create_dataset('signal', data=[1, 2], attrs={'units': 'm'})
    assert dataset[()].values.tolist() == [1, 2]
    assert dataset.values[()].tolist() == [1, 2]
    assert h.get_ureg() is h.get_ureg()
