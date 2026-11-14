# Repository guidelines

## Scope and workflow

The approved 3.0 implementation keeps scientific HDF5 I/O, xarray/Pint,
RDF/SPARQL, explicit SHACL validation, local queries, catalogs and Zenodo.
Conventions, layouts, HTTP server, Qt GUI, MongoDB and excluded analysis helpers
are removed. See [development](docs/development.md) and
[migration](docs/migration-3.md).

- Check `git status --short --branch` before editing and preserve existing work.
- Work on `feature/3.0-core`, based on main. Never commit on main.
- Before every staging operation and commit, verify the agreed branch with
  `git branch --show-current`; stop on another branch or detached HEAD.
- Stage explicit paths or reviewed hunks. Inspect `git diff --cached` and run
  `git diff --cached --check` before each commit. Commit coherent verified steps.
- Relevant Git operations are authorized. Never merge branches or PRs.
- Keep README, API documentation, guides and these instructions current together.
- Public documentation describes supported behavior and reproducible workflows.
  Keep agent discussions, implementation-session notes and decision deliberations
  under `.work/`; do not include them in published guides or README files.
  Mark historical examples explicitly and exclude them from the current build.
- `.playground/` and `.work/` are local experiments/evidence, outside production
  imports, test collection and commits. Consult archived experiments only when
  the task calls for them. Never commit credentials, user data, caches or builds.

## Release identity

Version metadata remains 2.9.0, DOI `10.5281/zenodo.24057487`, preparation date
2026-11-12 (Europe/Berlin), until the user provides a new reserved version-specific
3.0.0 Zenodo DOI in the existing version family. Do not reuse the old DOI, invent
an identifier or commit a placeholder. A reserved DOI need not resolve yet.

After receiving the DOI, update pyproject.toml, CITATION.cff, root codemeta.json,
Colab quickstart pin, changelog and README citation in one coherent commit.
Preserve historical releases, example DOIs, CodeMeta context and paper citation.
Runtime version comes from installed metadata; refresh the editable install.
`src/_build.py` generates packaged CodeMeta from the canonical root source.
Validate metadata and built artifacts. Tags, GitHub/Zenodo releases and PyPI
publication require separate explicit instructions. Never run `.build.bat`
during preparation: it uploads immediately.

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

## Architecture and compatibility

Source lives under `src/h5rdmtoolbox/`; tests mirror its retained feature areas.
`wrapper/` splits file/group/dataset/attribute implementations; `science/`
contains xarray I/O, units and calibration; `ld/` owns RDF; `validation/` owns the
shared SHACL service; `database/` owns local query/lazy access; `catalog/` and
`repository/` own discovery/publication. The facade loads features on demand.

Preserve Python >=3.10,<3.14 and existing HDF5 values, attributes, coordinates,
calibration references and RDF annotations. Deliberate API changes require a
migration entry. Keep explicit imports, four-space indentation, descriptive names
and NumPy-style public docstrings. Keep low-level imports independent of facade
initialization. No ordinary import creates directories, prunes caches, starts
network activity or installs application logging handlers.

Calibration is per open file, default False, and propagates to children/lazy
handles. `.values[...]` remains raw. SHACL validation is explicit and metadata-only
by default; scalar payload extraction requires an opt-in. Compare RDF graph
semantics and preserve literal lexical forms and datatypes. Keep RDF storage
mutation and validation separate, including existing partial-write behavior.

## Setup and verification

Use one interpreter from the repository root:

```bash
python -m pip install -e ".[test,docs]"
python -m pytest tests/test_startup.py tests/test_distribution.py -q
python -m pytest --cov=h5rdmtoolbox --cov-report=html
python -m pylint src/h5rdmtoolbox --rcfile=.pylintrc
python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html
```

Focused regression areas are tests/wrapper, tests/ld, tests/database,
tests/catalog and tests/repository. Test fixtures create isolated application
directories and restore configuration. Use tmp_path, tmp_h5_file/group/dataset;
do not write into tracked sample directories. For standalone scripts set
H5RDMTOOLBOX_USER_DATA_DIR, H5RDMTOOLBOX_CACHE_DIR and H5RDMTOOLBOX_LOG_DIR before
imports that exercise package features.

The full suite can read public resources. Wikidata requires its explicit opt-in.
Zenodo uploads require both H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1 and
ZENODO_SANDBOX_API_TOKEN. CI is read-only with no Zenodo write tokens. Never
reintroduce account-wide cleanup; manual cleanup requires explicit owned IDs.
Report failures and skips. For packaging changes verify the sdist-built wheel
outside the checkout. Measure startup and first-use costs separately with fresh
processes and isolated application directories. Capture baseline lint findings
and distinguish new diagnostics from existing ones.
