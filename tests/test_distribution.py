"""Build an sdist and verify its wheel outside the editable checkout."""

from email.parser import Parser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

from build import ProjectBuilder
from packaging.specifiers import SpecifierSet


def test_sdist_wheel_contains_resources_and_runs_independently(tmp_path):
    repository = Path(__file__).parents[1]
    canonical_metadata = (repository / 'codemeta.json').read_bytes()
    source = tmp_path / 'source'
    source.mkdir()
    for name in ('pyproject.toml', 'README.md', 'LICENSE', 'codemeta.json', 'MANIFEST.in'):
        shutil.copy2(repository / name, source / name)
    shutil.copytree(repository / 'src', source / 'src',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    artifacts = tmp_path / 'dist'
    sdist = ProjectBuilder(str(source)).build('sdist', str(artifacts))
    unpacked = tmp_path / 'sdist'
    unpacked.mkdir()
    with tarfile.open(sdist) as archive:
        for entry in archive.getmembers():
            destination = (unpacked / entry.name).resolve()
            assert unpacked.resolve() in destination.parents
            assert not entry.issym() and not entry.islnk()
        extraction_options = {'filter': 'data'} if hasattr(tarfile, 'data_filter') else {}
        archive.extractall(unpacked, **extraction_options)
    sdist_source, = unpacked.iterdir()
    assert (sdist_source / 'src' / '_build.py').is_file()
    assert (sdist_source / 'codemeta.json').is_file()
    wheel = ProjectBuilder(str(sdist_source)).build('wheel', str(artifacts))
    installed = tmp_path / 'wheel'
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for name in ('data/codemeta.json', 'data/style.css'):
            assert 'h5rdmtoolbox/' + name in names
        excluded = ('.playground/', '.work/', 'h5rdmtoolbox/llm/',
                    'h5rdmtoolbox/convention/', 'h5rdmtoolbox/layout/',
                    'h5rdmtoolbox/gui/', 'h5rdmtoolbox/server/',
                    'h5rdmtoolbox/server.py', 'h5rdmtoolbox/database/mongo.py',
                    'h5rdmtoolbox/plotting.py', 'h5rdmtoolbox/ld/metrics.py')
        assert not any(name.startswith(excluded) for name in names)
        assert any(name.endswith('/LICENSE') for name in names)
        metadata_path, = [name for name in names if name.endswith('.dist-info/METADATA')]
        metadata = Parser().parsestr(archive.read(metadata_path).decode('utf-8'))
        version = metadata['Version']
        supported = SpecifierSet(metadata['Requires-Python'])
        assert '3.9' not in supported
        assert '3.14' not in supported
        for python_version in ('3.10', '3.11', '3.12', '3.13'):
            assert python_version in supported
        classifiers = {value.removeprefix('Programming Language :: Python :: ')
                       for value in metadata.get_all('Classifier', [])
                       if value.startswith('Programming Language :: Python :: ')}
        assert classifiers == {'3.10', '3.11', '3.12', '3.13'}
        assert archive.read('h5rdmtoolbox/data/codemeta.json') == canonical_metadata
        archive.extractall(installed)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("COV_CORE_")}
    for key, folder in (('H5RDMTOOLBOX_USER_DATA_DIR', 'data'),
                        ('H5RDMTOOLBOX_CACHE_DIR', 'cache'), ('H5RDMTOOLBOX_LOG_DIR', 'log')):
        env[key] = str(tmp_path / 'runtime' / folder)
    script = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import h5rdmtoolbox as h
assert Path(h.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
assert h.get_package_meta()['version'] == h.__version__ == sys.argv[2]
assert h.get_package_meta()['@id'] == sys.argv[3]
with h.File('measurement.hdf', 'w') as handle:
    assert handle.create_dataset('data', data=[1, 2])[()].values.tolist() == [1, 2]
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, str(installed), version,
                             json.loads(canonical_metadata)['@id']],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
