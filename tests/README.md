# Testing

Run commands from the repository root using the same Python interpreter.
The package supports Python 3.9-3.13; `pyproject.toml` is the source of truth.

```bash
python -m pip install -e ".[test]"
python -m pytest tests/test_version.py tests/test_config.py tests/test_cli.py -q
python -m pytest --cov=h5rdmtoolbox --cov-report=html
```

HTML coverage is written to `htmlcov/index.html`; `.coverage` and subprocess
coverage files named `.coverage.*` are ignored local artifacts. Choose focused tests using the
[source/test map](../AGENTS.md). Static analysis uses the existing configuration:

```bash
python -m pylint h5rdmtoolbox --rcfile=.pylintrc --output=.pylint
```

## Isolation and external resources

`tests/conftest.py` configures unique temporary application data, cache, and log
directories before importing the package and resets the active convention around
each test. Use its HDF5 fixtures or `tmp_path` for generated files. Restore other
global configuration explicitly. Checked-in sample files are inputs, not output
locations. For scripts run outside pytest, set all three application directory
environment variables before importing the package; see the
[developer overview](../docs/development.md).

Catalog/store tests place generated HDF5 files and local databases under
`tmp_path`, separately for each test. Their checked-in RDF/JSON-LD inputs remain
read-only. Tests can be run individually without relying on a previous test's
generated files or deleting a shared source-tree database directory.

The full suite still includes public resource downloads and service integrations.
It is not an offline suite. Use `-rs` to see skip reasons; a skipped integration
is not evidence that its behavior was verified.

## Live Zenodo Sandbox uploads

Tests marked `zenodo_upload` create remote Sandbox deposits. They run only when
both `H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1` and a nonempty
`ZENODO_SANDBOX_API_TOKEN` are present. A token by itself never enables uploads.
Set the token in your local environment, then opt in explicitly. For PowerShell:

```powershell
$env:H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS = '1'
python -m pytest -m zenodo_upload -rs
```

For bash:

```bash
H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1 python -m pytest -m zenodo_upload -rs
```

Existing Python-version restrictions still apply; inspect skip reasons. Keep
credentials out of version control. The test application directories are
isolated, so local user `zenodo.ini` files are not reused by the suite.

## CI and manual cleanup

The test workflow runs on pushes, pull requests, and manual dispatch. It preserves
the supported Python/OS matrix, uses read-only repository permissions, and does
not receive Zenodo credentials. Upload and Wikidata opt-ins are explicitly off.
Coverage upload is restricted to push events. Public resource reads still occur;
these checks are not an offline test selection.

There is no automatic Sandbox cleanup job. Opted-in integration tests clean their
own records in `finally` blocks. If manual cleanup is needed, first identify and
verify the specific Sandbox deposition IDs you own, configure Sandbox credentials
locally, then run:

```bash
python -m tests.clean_zenodo_sandbox 12345 67890
```

The example IDs are placeholders, not records to delete. The tool rejects empty
or invalid selections before making requests, deletes duplicate IDs only once,
uses a fixed Sandbox endpoint with a timeout, and stops on HTTP errors. It never
lists account drafts or follows arbitrary deletion URLs. Its automated tests
mock all requests; they perform no real deletion.

## Wikidata and MongoDB

Wikidata Query Service tests require `H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1`; select
them with `python -m pytest -m wikidata -rs`. This opt-in does not enable uploads.

MongoDB tests probe a local server and can fall back to mongomock on Python below
3.13. On Python 3.13, the affected tests skip if a real server is unavailable.
Server/GUI and other optional features require their corresponding extras;
check test skip reasons when validating changes in those areas.
