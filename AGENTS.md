# Repository Guidelines

## Purpose and orientation

`h5rdmtoolbox` supports FAIR research data management with HDF5: metadata-aware
`h5py` wrappers, scientific conventions, xarray/pint integration, RDF export and
validation, queries, and repository publication. Read
[the developer overview](docs/development.md) for data flow, import dependencies,
and the prioritized maintenance backlog.

## Workspace and Git workflow

- Check `git status --short --branch` before editing. Preserve existing work.
- Create or use the task's agreed working branch before changing files. For this
  modernization, use `feature/modernize-repository`.
- **Never commit on `main`.** Before every staging operation and commit, run
  `git branch --show-current` and verify the agreed branch. Stop if the branch
  differs or HEAD is detached.
- `.playground/` contains ignored local experiments and archived code ideas.
  Keep it outside production imports, test collection, documentation sources,
  and commits. Consult it only when the task calls for those ideas.
- Stage explicit paths or reviewed hunks. Inspect `git diff --cached` and run
  `git diff --cached --check` before committing; avoid blanket staging commands.
- Commit regularly after each coherent, verified step, using a short, specific
  imperative subject. Keep unrelated changes in separate commits. Make routine
  commits on the agreed non-main branch without asking for confirmation.
- Report completed checks and any failures or skips. Pushes, merges, and releases
  require a task that calls for them.
- Keep documentation, including `README.md`, current with every change. Review
  the README alongside affected API docstrings, user guides, developer overview,
  and agent instructions; update them in the same commit
  whenever behavior, architecture, or development workflows change.

## Subagents and collaborative investigations

- Before starting any subagent, ask the user for explicit approval of the
  proposed delegation. State the topic, purpose, number of agents, and whether
  they will investigate, discuss alternatives, or edit code. Wait for approval.
- Use subagents when architecture, quality, features, decisions, or difficult
  problems benefit from independent investigation or discussion. Approval is
  scoped to the agreed delegation; ask again before starting additional agents.
- Each approved investigation uses `.work/<topic>/` with a descriptive topic
  name. Agents document their evidence, findings, options and tradeoffs, open
  questions, recommendations, and relevant checks there. Give agents separate
  report files and explicit edit ownership to avoid concurrent file conflicts.
- Record the discussion and final synthesis in that topic folder, including
  disagreements and the rationale for the chosen approach. Link relevant source
  paths and checks; never put credentials or sensitive runtime data in reports.
- Review agent findings before applying changes, and carry accepted decisions
  into the affected production code, README, and developer/user documentation.

## Source map and focused tests

Paths below are relative to the repository root. `tests/` mirrors package areas,
with plural `conventions/` and `layouts/` test directories.

| Area | Source | Focused tests |
| --- | --- | --- |
| HDF5 objects, attributes, decoders, accessors | `h5rdmtoolbox/wrapper/` | `tests/wrapper/`, `tests/test_xarray_export.py` |
| Metadata conventions and dynamic signatures | `h5rdmtoolbox/convention/` | `tests/conventions/` |
| HDF5 layout validation | `h5rdmtoolbox/layout/` | `tests/layouts/` |
| RDF, SPARQL, SHACL, graph metrics | `h5rdmtoolbox/ld/` | `tests/ld/` |
| HDF5 queries, lazy objects, MongoDB | `h5rdmtoolbox/database/` | `tests/database/`, `tests/wrapper/test_lazy.py` |
| Data catalogs and stores | `h5rdmtoolbox/catalog/` | `tests/catalog/` |
| Repository interface and Zenodo | `h5rdmtoolbox/repository/` | `tests/repository/` |
| CLI implementation; package CLI shim | `h5rdmtoolbox_cli.py`; `h5rdmtoolbox/cli.py` | `tests/test_cli.py` |
| HTTP server; templates and static assets | `h5rdmtoolbox/server.py`; `h5rdmtoolbox/server/` | `tests/test_server.py` |
| Configuration, directories, utilities, display | `h5rdmtoolbox/_cfg.py`, `h5rdmtoolbox/user.py`, `h5rdmtoolbox/utils/`, `h5rdmtoolbox/_repr.py` | `tests/test_config.py`, `tests/test_user.py`, `tests/test_utils.py`, `tests/test_repr.py` |
| Scientific extensions and plotting | `h5rdmtoolbox/extensions/`, `h5rdmtoolbox/plotting.py` | `tests/test_extensions.py`, `tests/test_plotting.py` |

`h5rdmtoolbox/gui/` contains the optional Qt GUI. Documentation lives in `docs/`;
package assets and sample conventions live in `h5rdmtoolbox/data/`.

## Setup and checks

Run commands from the repository root using the same Python interpreter:

```bash
python -m pip install -e ".[test]"
python -m pytest tests/test_version.py tests/test_config.py tests/test_cli.py -q
python -m pytest tests/path/to/test_file.py -q
```

For broad implementation changes, run the full suite and coverage:

```bash
python -m pytest --cov=h5rdmtoolbox --cov-report=html
python -m pylint h5rdmtoolbox --rcfile=.pylintrc --output=.pylint
```

Capture existing lint failures before broad refactors and distinguish them from
new findings. Preserve the current tools and formatting style unless changing
them is part of the task.

For prose and navigation changes, install docs dependencies and build HTML
without executing notebooks. The current Sphinx 8 documentation environment
requires Python 3.10+, while the base package continues to support Python 3.9:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html
```

For notebook behavior changes, omit `-D nb_execution_mode=off` so the configured
execution policy applies. Review warnings as well as the exit status. The CLI
entry point is `h5tbx`, mapped to `h5rdmtoolbox_cli:h5tbx`.

## Test isolation and external dependencies

- `tests/conftest.py` sets unique temporary data/cache/log directories before
  package import, resets the active convention around each test, and provides
  `tmp_h5_file`, `tmp_h5_group`, and `tmp_h5_dataset` fixtures. Reuse these fixtures
  or `tmp_path`; do not write generated data into tracked sample directories.
- For standalone import benchmarks or scripts exercising user-directory resets,
  set `H5RDMTOOLBOX_USER_DATA_DIR`, `H5RDMTOOLBOX_CACHE_DIR`, and
  `H5RDMTOOLBOX_LOG_DIR` to disposable locations **before** importing the package.
  Import creates directories and can prune old cache files.
- Some tests download remote resources or use Zenodo credentials. Wikidata tests
  are skipped unless `H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1`. There is no universal
  offline test marker; do not describe the full suite as offline.
- Tests marked `zenodo_upload` require both
  `H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1` and `ZENODO_SANDBOX_API_TOKEN`.
  Supplying credentials alone does not enable remote writes. Check skip reasons
  with `python -m pytest -m zenodo_upload -rs`; existing Python-version skips
  still apply. See `tests/README.md` for the integration-test workflow.
- MongoDB tests probe a local server and can fall back to mongomock on Python
  below 3.13. Optional server tests may skip when their dependencies are absent.
  Install the relevant extra for changes in those areas and check skip reasons.
- Add meaningful regression tests for changed behavior. For RDF changes, compare
  graph semantics rather than incidental triple order, unless output formatting
  is itself the contract. Documentation-only changes need documentation checks,
  not new behavioral tests.

## Refactoring and compatibility

- Preserve Python `>=3.9,<3.14`, public import paths, signatures, defaults,
  exceptions, HDF5 metadata conventions, and RDF semantics unless the task
  explicitly authorizes a compatibility change.
- Follow existing style: four spaces, descriptive snake_case, PascalCase classes,
  explicit imports, and NumPy-style public docstrings.
- Extract common behavior only where semantics agree. Inspect existing helpers
  before introducing another abstraction; separate behavior fixes from refactors.
- Prefer imports from defining internal modules over new back-imports through
  the package facade where this avoids cycles. Check initialization order before
  changing existing imports. Preserve shared unit-registry identity, convention
  activation, decoder registration, and accessor registration.
- Keep expensive or optional feature imports at their point of use when safe;
  CLI help already delays package imports until command execution. Measure
  startup changes in fresh processes with isolated application directories,
  record environment and repeated timings, and test the first use of deferred
  features. Use `-X importtime` for attribution, not as a wall-time benchmark.
  Run `python -m pytest tests/test_startup.py -q` to check deferred engine imports
  and first-use behavior in a fresh process.
- Required dependencies and feature extras are defined in `pyproject.toml`.
  Reuse existing extras and pins; avoid silently changing installation contracts.

## Credentials and generated files

Use environment variables such as `ZENODO_SANDBOX_API_TOKEN` for secrets. Never
commit tokens, local `zenodo.ini`, user data, logs, coverage reports, build output,
or caches. PR descriptions should explain behavior, validation, and any new
optional dependency or configuration; include screenshots when they help review
visible GUI or documentation changes.
