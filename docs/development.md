# Developer overview and maintenance priorities

This overview describes the active repository on the modernization branch,
based on version 2.8.2 (`30b6970f`) and updated with the changes below. It is intended for contributors and
coding agents. The root `AGENTS.md` contains the day-to-day working instructions.

## What the toolbox does

The toolbox helps researchers carry metadata through the HDF5 research data
lifecycle: define conventions, collect data, analyze quantities, describe data
semantically, publish files, and find them again. Its main Python entry point is
`import h5rdmtoolbox as h5tbx`. `h5tbx.File`, `Group`, and `Dataset` extend `h5py`
objects; dataset reads can return xarray objects with coordinates and physical
units. This is the central behavior to protect during refactoring.

Validation has three complementary forms: conventions validate metadata
attributes, layouts check HDF5 structure, and SHACL validates an RDF graph
derived from the file. They serve different contracts and should not be merged
solely because they all perform validation.

## Responsibilities and data flow

| Area | Responsibility and important relationships |
| --- | --- |
| Package facade (`h5rdmtoolbox/__init__.py`) | Public re-exports, configuration access, default convention activation, logging, and convenience functions. Some functions already delegate through local imports. |
| `wrapper/` | HDF5 files, groups, datasets, attributes, accessors, and xarray conversion. It consults conventions and configuration and attaches RDF metadata. |
| `convention/` | Loads and registers metadata rules, validates attributes, and changes wrapper method signatures and decoder selection when a convention is activated. |
| `layout/` | Describes and validates HDF5 object structure through queries. |
| `ld/` | Combines structural graphs from `ld/hdf/` with contextual graphs from `ld/user/`; provides RDF attribute handling, serialization, SPARQL, metrics, and SHACL. |
| `database/` | Queries HDF5 objects and exposes lazy results; contains the optional MongoDB integration. The public `lazy` helper is imported by the package facade. |
| `catalog/` | Coordinates metadata and data stores, local indexing, and remote SPARQL queries. Uses wrappers, RDF, pandas, and repository resources. |
| `repository/` | Defines the repository interface and Zenodo record, download, metadata, and upload behavior. Convention loading also uses this integration. |
| `utils/`, `_cfg.py`, `user.py`, `_repr.py` | Shared file/network/HDF5 helpers, mutable configuration and unit registry, application directories, and text/notebook representations. Configuration access uses `_cfg.py` directly, and utilities use the named package logger. |
| `extensions/`, `plotting.py` | Dataset accessors and scientific operations, plus plotting support for xarray data and unit-aware labels. |
| `h5rdmtoolbox_cli.py` | Implements the `h5tbx` console entry point. `h5rdmtoolbox/cli.py` delegates to it. Heavy package imports are delayed until command execution. |
| `server.py`, `server/`, `gui/` | `server.py` implements HTTP inspection; `server/` holds templates and static assets. `gui/` contains the optional Qt application. |

A typical route through the package is:

```text
Python caller or CLI command
  -> wrapper.File / Group / Dataset
     -> convention rules + configuration + xarray/pint decoding
     -> HDF5 attributes, coordinates, and RDF annotations
  -> ld: structural graph + contextual graph
     -> RDF serialization / SPARQL / SHACL / metrics
  -> repository publication or catalog indexing and discovery
```

This is a functional overview, not a strict dependency hierarchy. For example,
the wrapper imports RDF support and convention code imports wrapper decoders.
Refactors must account for the actual import
order before enforcing new boundaries.

`pyproject.toml` is the installation contract. NumPy, h5py, xarray, pint,
pint_xarray, RDFLib, PySHACL, IPython, and matplotlib are currently required
dependencies. Extras include `database`, `catalog`, `csv`, `snt`, `gui`, and
`server`; test and documentation extras compose additional requirements.
Deferring an import does not by itself justify changing a required dependency
into an extra.

## Initialization and shared state

Importing the facade does more than expose symbols:

- `user.py` creates application data, cache, log, and session directories.
  Constructing `UserDir` also prunes old cache files.
- The facade installs stream and delayed file logging handlers.
- `_cfg.py` constructs the shared Pint `UnitRegistry`; the facade assigns it to
  `pint_xarray.unit_registry`.
- Convention, wrapper, utility, database, RDF, and SHACL modules are imported.
  PySHACL is loaded when validation runs; IPython display support is loaded when
  HTML output is displayed. Neither is loaded by a plain toolbox import.
- The default `h5py` convention is registered and selected. The bundled `h5tbx`
  convention is already built lazily when first selected.
- An exit handler cleans session data, and an xarray display option is set.

The active convention pointer uses a `ContextVar`, but wrapper method signatures
and decoder names are still changed globally. This is not sufficient evidence
of thread/task isolation. Configuration, the registry, accessor registration,
and logging also have process-wide effects.

Fresh contexts resolve an unset convention pointer to the registered empty
`h5py` convention. This lookup does not activate global signatures or decoders;
explicit activation still inspects the raw context pointer. Before the default
convention is registered during package initialization, lookup may return None.

Contextual RDF export does not infer dates from string attributes. Use explicit
RDF Literal annotations for date and dateTime values; lexical strings such as
dimension counts and sample identifiers must survive serialization unchanged.
The focused regressions are `tests/conventions/test_context_state.py` and
`tests/ld/test_literal_preservation.py`. This is a deliberate change from
heuristic date typing; existing explicit annotations remain supported.
Explicit non-language literals now use a `$type: rdflib.term.Literal` JSON
descriptor with lexical value, datatype, and `normalize: false` in RDF object
mapping attributes. This deliberately replaces their previous bare-string
storage, which lost the datatype. Language-literal descriptors retain their
existing representation. Legacy bare strings remain readable as strings.

For standalone benchmarks, documentation builds, and scripts that reset user
directories, set these environment variables to disposable locations before
the first package import:

```text
H5RDMTOOLBOX_USER_DATA_DIR
H5RDMTOOLBOX_CACHE_DIR
H5RDMTOOLBOX_LOG_DIR
```

Pytest already does this in `tests/conftest.py`. It also resets the active
convention before and after each test and provides temporary HDF5 fixtures.
Tests changing other global settings must restore them explicitly.

## Checks and initial measurements

The following local smoke check passed during the initial audit on Windows with
CPython 3.12.4:

```bash
python -m pytest tests/test_version.py tests/test_config.py tests/test_cli.py -q
```

Result: **32 passed**. This covers version consistency, configuration behavior,
CLI dispatch, and selected serialization paths; it is not a full-suite result.
Existing dependency deprecations and a missing-file-URI warning were observed.

The full suite includes remote downloads and credential/service-dependent tests.
Wikidata tests are opt-in through `H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=1`. MongoDB tests
probe a local server, with mongomock fallback on Python below 3.13. There is no
single offline marker covering all external I/O. Check individual test modules
and skip reasons before choosing a local verification set.

The latest full coverage run on Windows/CPython 3.12.4 with required server
validation produced **558 passed, 27 skipped, and no failures**. Live uploads and
Wikidata opt-ins were disabled; other public resource downloads still ran.
An earlier run exposed an unguarded Sandbox upload returning HTTP 403 without
a token. Live upload tests now carry the `zenodo_upload` marker and require both explicit
`H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1` and `ZENODO_SANDBOX_API_TOKEN`.
The directly affected import-refactor test selection passed all 113 tests.
Targeted Pylint reports retained the 9.07/10 baseline, with no new
diagnostics after accounting for the renamed configuration import.

Collection-policy regression tests exercise opt-in/credential combinations in
isolated pytest processes using a dummy upload, so they perform no remote writes.
Wikidata opt-in is independent of the upload gate. See `tests/README.md` for the
current integration commands; Python-version restrictions on existing tests
remain in effect.

For prose and navigation, build without notebook execution:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html
```

The pre-change documentation baseline built successfully without Sphinx warnings
with notebook execution disabled. Notebook edits require a separate build using
the configured execution policy. `tests/README.md` documents current setup,
isolation, and integration-test opt-ins. `pyproject.toml` remains the source of
truth for supported Python versions and dependencies.

### Startup measurement protocol

Three sequential fresh Python processes, each with new application directories,
took **4.704 s, 4.971 s, and 4.627 s** in the initial Windows/CPython 3.12.4 audit
on 2026-10-31. The median was **4.704 s**. These are process wall times including
interpreter startup, package import, and exit cleanup, measured before archiving
the local experiments. They are an indicative local baseline, not an isolated
import duration or a portable performance threshold.

Use the same interpreter, environment, directory/cache conditions, and sequential
fresh-process protocol for comparisons. Measure CLI help and the first use of
any deferred feature separately so moving work out of import does not hide a
first-use regression. For example, this script reproduces the process benchmark:

```python
import os
import pathlib
import statistics
import subprocess
import sys
import tempfile
import time

samples = []
with tempfile.TemporaryDirectory(prefix="h5rdmtoolbox-startup-") as root:
    for index in range(3):
        env = os.environ.copy()
        for key, folder in (
            ("H5RDMTOOLBOX_USER_DATA_DIR", "data"),
            ("H5RDMTOOLBOX_CACHE_DIR", "cache"),
            ("H5RDMTOOLBOX_LOG_DIR", "log"),
        ):
            env[key] = str(pathlib.Path(root) / str(index) / folder)
        start = time.perf_counter()
        subprocess.run(
            [sys.executable, "-c", "import h5rdmtoolbox"],
            env=env, check=True, capture_output=True, text=True,
        )
        samples.append(time.perf_counter() - start)
print("Process wall times:", samples)
print("Median:", statistics.median(samples))
```

Use `python -X importtime -c "import h5rdmtoolbox"` with isolated application
directories to attribute import costs. Its instrumentation changes timing;
do not mix those numbers with the process benchmark.

## DOI-first release checklist

Release **2.8.4** is prepared on `fix/context-defaults-and-rdf-literals` from
`main`, with the user-supplied reserved DOI `10.5281/zenodo.24057487` and
preparation date **2026-11-08** (Europe/Berlin). Its release notes include the
context-default and explicit RDF literal fixes. Publication remains a separate
action. The previous release preparation is retained below for reference.

Release **2.8.3** is prepared on `release/2.8.3` from
`feature/modernize-repository`, with the user-supplied reserved DOI
`10.5281/zenodo.23854129` and release date **2026-11-01**. Publication is a separate
step; a reserved DOI may not yet resolve. This checklist also applies to future
versions, using their agreed version and release branch.

### Reserve the identity before updating files

The user creates a **new-version draft in the existing Zenodo version family**
and supplies its reserved, version-specific DOI. Do not create an unrelated
deposit, reuse the previous release DOI, substitute a concept DOI, or use a
placeholder. Zenodo allows a DOI to be reserved before uploading the archive;
it is registered on publication, so failure to resolve a reserved DOI is not
an error. See [DOI reservation](https://help.zenodo.org/docs/deposit/create-new-upload/)
and [record versioning](https://help.zenodo.org/docs/deposit/manage-versions/).

### Update the release consistently

After receiving the DOI, update these values in one coherent commit:

| Source | Required release update |
| --- | --- |
| `pyproject.toml` | `[project].version` |
| `CITATION.cff` | `version`, release DOI, and `date-released` |
| Root `codemeta.json` | `version` and the DOI URL in `@id` |
| `docs/colab/quickstart.ipynb` | Pinned installation version in the first cell |
| `CHANGELOG.md` and README | New release notes and an explicitly version-labelled software citation |

Use the preparation date in Europe/Berlin unless the user supplies a different
release date. Keep author identities unchanged unless separately verified.
Preserve historical changelog entries and audit reports, example/dataset DOIs,
the CodeMeta context DOI, and the paper citation. Link the README software
citation to the supplied release DOI and label it with the version; do not
assume a fixed record URL always points to the latest release.

`h5rdmtoolbox/_version.py` reads installed distribution metadata via
`importlib.metadata`. Refresh the editable installation from the current
checkout after editing the version. Do not add a second version constant or
hand-edit `h5rdmtoolbox/data/codemeta.json`: `_build.py` copies the canonical root
metadata during builds, and editable imports fall back to the root source.

After moving/copying a checkout, ignored local `h5rdmtoolbox.egg-info` metadata
can shadow the freshly installed version. Check `importlib.metadata.version`
and `h5rdmtoolbox.__version__` before validation. If that local metadata is stale,
regenerate it from the current project with
`python -c "from setuptools import setup; setup()" egg_info`, then verify the
version again. Do not change `_version.py` to conceal an installation mismatch.

### Verify and prepare the handoff

```bash
python -m pip install -e ".[test]"
python -m pytest tests/test_version.py tests/test_distribution.py tests/wrapper/test_core.py -q
python -m pytest --cov=h5rdmtoolbox --cov-report=html
python -m sphinx -b html -W -D nb_execution_mode=off docs docs/_build/html
```

Use the same interpreter throughout. Set
`H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=0` and
`H5RDMTOOLBOX_RUN_WIKIDATA_TESTS=0` for release validation. Install `.[test-server]`
and set `H5RDMTOOLBOX_REQUIRE_SERVER_TESTS=1` when requiring server coverage;
otherwise report optional skips. The full suite can still read public resources.
The docs environment requires Python 3.10+ and `.[docs]`.
Before building docs, point `H5RDMTOOLBOX_USER_DATA_DIR`,
`H5RDMTOOLBOX_CACHE_DIR`, and `H5RDMTOOLBOX_LOG_DIR` at disposable directories
under `.playground/`, since autodoc imports the package. After moving a checkout,
use Sphinx's `-E` option and a fresh output directory to avoid stale build state.

Version tests check package, citation, CodeMeta, and notebook agreement, plus
exact DOI agreement and a valid release date without querying Zenodo. The RDF
wrapper test derives its expected software version from `__version__`. The
distribution test builds an sdist and wheel from fresh sources, checks the
packaged CodeMeta bytes against the canonical source, and verifies its version
and DOI through an import outside the checkout.

Commit the verified preparation on the release branch. At a separately requested
publication step, use the reviewed release commit for the archive and builds,
match Zenodo's version/date/creators/license to the reviewed metadata, and upload
to the same reserved draft. The planned archive is a source ZIP; generated build
files, local experiments, caches, and credentials must not enter it. Git tags,
GitHub releases, Zenodo publication, and PyPI uploads are separate actions.
Never use `.build.bat` as a validation command: it builds and immediately uploads
`dist/*` to PyPI. No release automation or `.zenodo.json` is introduced here.

## RDF metadata storage contract

The RDF storage refactoring is developed on `feature/refactor-rdf-storage`.
Its scope is Python implementation and architecture: written HDF5 metadata must
remain unchanged. Public `rdf`/`frdf` managers, `Attribute`, tuple assignment,
and `attrs.create(...)` remain the supported entry points.

`tests/ld/test_rdf_storage.py` characterizes the original implementation before
refactoring (47 passing cases). It bypasses wrapper getters to check exact JSON
text, scalar UTF-8 string types, list shapes, attribute names, append/duplicate
behavior, empty mappings, and reopened files. It covers root groups, nested
groups, datasets, file-level metadata, blank nodes, literals, JSON-LD, and
`ontolutils.Thing` values. Existing graph/query tests complement these checks.

The refactored implementation separates three responsibilities:

| Layer | Responsibility |
| --- | --- |
| `ld/rdf.py` | Public managers, URL/type validation, and preparation of individual RDF objects. Small helpers handle literal encoding and single-entry JSON-LD graphs without HDF5 access. |
| `ld/_rdf_storage.py` | Shared mapping replacement, object append, entry removal, and type merging. It preserves scalar/list transitions, duplicate behavior, and empty mappings. Each mapping adapter lives for one operation, avoiding stale manager caches. |
| `wrapper/h5attr.py` and existing attribute utilities | Actual attribute assignment and HDF5 encoding, including JSON formatting, string types, and existing convention hooks. These writers are unchanged. |

The public module continues to export the same managers, helpers, and constants.
The internal storage module imports only `json`, and does not depend on wrapper,
RDFLib, Pydantic, or package-facade initialization. Sequence orchestration remains
at the public entry points so the adapter does not change validation or write order.

The contract selection now includes 52 cases. A local differential audit loaded
the pre-refactor module from commit `25e00360` alongside the new implementation
and replayed 81 operations. After each operation, raw attributes, datatypes,
shapes, dataset values, exceptions, and warnings were identical; reopening the
files also gave identical stored attributes. The disposable comparison artifacts
remain under ignored `.playground/`; the permanent contract tests are in `tests/ld/`.

Verification on Windows/CPython 3.12.4 passed the focused RDF/wrapper/startup
selection (252 tests), the full coverage suite (558 passed, 27 skipped), and
Sphinx with `-W` and notebook execution disabled. The targeted Pylint score
remains 9.20/10, and the full-package score remains 8.75/10 against a separate
copy of the original tracked package. Pylint still exits nonzero for existing
findings. Non-cycle diagnostics introduce no new messages and remove two old
ones; both package reports contain 55 import-cycle diagnostics, whose reported
paths vary with traversal order. The new storage module adds only a `json` import.

Preserve validation and mutation order as well as final values. Sequence writes
can retain earlier elements when a later element is rejected. `IRIDict.object`
and the mapping-style object setter have different sequence handling; predicates
and objects also differ in URL normalization. File-predicate entry points have
historical routing differences. Changing these behaviors belongs in a separate
behavior change, with a deliberate storage compatibility decision.

## Prioritized maintenance backlog

The two-agent review and parent verification are recorded in
`.work/architecture-quality/README.md`, with separate architecture and quality
reports. They identified additional correctness gaps that the editable-install
test suite does not expose: automatic account-wide Sandbox cleanup in CI,
missing installed metadata/resources, and same-instance Convention restoration.
The default CI write/cleanup and installed metadata issues have since been
addressed below, along with sequential convention restoration. Full concurrency
isolation remains a separate design question. The reports
preserve baseline evidence, alternatives, and acceptance checks; see completed
changes here for subsequent fixes.

The pinned Sphinx 8 documentation environment and base package require Python 3.10+.

### Completed refactorings

Python support now starts at 3.10. In main-branch run
[42573771162](https://github.com/matthiasprobst/h5RDMtoolbox/actions/runs/42573771162/attempts/1),
the Ubuntu/Python 3.9 job failed during interpreter setup after `ubuntu-latest`
moved to Ubuntu 26.04; the other 14 matrix jobs and the server job passed.
The matrix now covers Python 3.10-3.13 on all three operating systems, matching
the package requirement, classifiers, and CodeMeta metadata. CI policy tests
guard the supported versions, and the distribution test checks built metadata.
The later rerun reported a separate GitHub Actions startup error before jobs ran.

Scale/offset decoding now removes both calibration role flags before every
processing branch. The former cleanup duplicated `IS_DATA_SCALE`, concatenated
the scale/offset reference names, and missed transformed results due to early
returns. `tests/wrapper/test_decoders.py` covers all four transform combinations,
path and dataset references, values, units, coordinates, and preservation of raw
HDF5 calibration metadata. The decoder/file/context selection passed 41 tests.

The first hosted server job passed, while the core matrix on macOS/Python 3.13
exposed a Pint 0.26.2 parsing incompatibility in `AttributeString.to_pint()`.
That failure was reproduced locally using an isolated copy of the same Pint
version. Square-bracket annotations now normalize to parentheses only for
parsing, preserving existing attribute storage and quantity semantics. New
regressions cover file/group/dataset attributes, compound units, powers, negative
scientific notation, and unchanged stored text. The matrix now keeps independent
jobs running after a failure, so one result does not hide the other combinations.
Focused checks passed with both Pint 0.25.2 (76 tests) and Pint 0.26.2 (74 tests);
the selections included the attribute regressions and existing wrapper tests.
Hosted run
[41235572426](https://github.com/matthiasprobst/h5RDMtoolbox/actions/runs/41235572426)
for commit `c8cb559c` passed all 15 Python/OS combinations and the server job.
The earlier failed baseline is run
[41222928487](https://github.com/matthiasprobst/h5RDMtoolbox/actions/runs/41222928487).

Optional server tests now have a single missing-dependency boundary instead of
82 repeated skip annotations. Missing FastAPI/HTTPX can skip optional runs;
required server runs and broken installed dependencies fail visibly. The
`test-server` extra combines existing feature/test extras with HTTPX. A dedicated
Ubuntu/Python 3.12 CI job runs the server suite in required mode and validates
actual passing cases with no skips in its JUnit report. Other Python/OS coverage
remains in the main matrix. Local import-policy and report-policy tests cover
the failure paths; the hosted server job passed in the run linked above.

Checkout/setup-python/cache actions now use Node 24-compatible v6/v6/v5 releases
on the existing GitHub-hosted runners. Their documented minimum runner version
is 2.327.1; self-hosted reuse must meet it. See the official
[checkout](https://github.com/actions/checkout#checkout-v5),
[setup-python](https://github.com/actions/setup-python#breaking-changes-in-v6),
and [cache](https://github.com/actions/cache#whats-new) runtime notes. Action major
updates preserve the configured inputs, permissions, and Python matrix. Hosted
execution passed for all supported Python versions on Linux, macOS, and Windows.

Convention objects now keep a separate existing `use` manager for every entry,
so repeated same-instance nesting restores each previous convention on exit.
Return identity and immediate activation by `use(...)` are preserved. New local
regressions block network requests and cover two/three levels, mixed instances,
exceptions, re-entry, and an entry failure before activation, checking signatures
and dataset decoding as well as the context pointer. This does not provide
transactional rollback of partially failed signature insertion or concurrent
thread/task isolation. Getter/class docstrings now distinguish context-local
lookup from the process-global activation effects.

`get_package_meta()` now reads package data in a built distribution, with an
editable-checkout fallback to the canonical root metadata. A small setuptools
build command (`_build.py`) copies that one source into the built package; the
sdist includes the source and command. The convention HTML template declaration
uses its actual singular directory. The distribution regression builds from a
fresh source copy through sdist to wheel, inspects metadata/resources/license,
and exercises the artifact's metadata API and HDF5 read in isolated Python.
Test extras include the frontend/backend tools so this check needs no build
dependency downloads. Release builds should use clean sources rather than old
working-tree `build/lib` output. The review's wheel failures describe the baseline.

The test workflow now includes pull requests and manual dispatch, uses read-only
repository permissions, disables live upload/Wikidata opt-ins, and receives no
Zenodo write credentials. Automatic account-wide cleanup was removed. The manual
cleanup tool now validates an explicit list of positive deposition IDs, deletes
only those IDs at the fixed Sandbox endpoint with a timeout, and stops on errors.
Mock-based ownership and workflow tests pass without deleting remote records.
Hosted GitHub execution passed in the run linked above; cleanup checks used mocks.

Catalog tests now keep generated HDF5 data and local databases under per-test
`tmp_path` directories. Checked-in metadata remains read-only, and individual
tests no longer share or delete a source-tree working database. Identical
catalog initialization branches were consolidated into one path.

Wrapper objects, dataset decoders, representations, and HDF5 utilities obtain
configuration and unit-registry access from `_cfg.py` rather than facade
re-exports. Utility loggers use `logging.getLogger("h5rdmtoolbox")`, preserving
the same logger and handlers without dynamically importing the package facade.
Download utilities obtain the user-data directory from its defining module.
These changes remove initialization-order dependencies on facade attributes;
public exports and shared registry/logger identities remain unchanged.

Configuration validation now checks every plotting-name entry and accepts
`None` for both compression defaults. All options are checked before updates;
setting and restoring `ureg_format` use the same routine so nested contexts and
exceptions restore the shared Pint formatter as well as the configuration dict.
Regression tests in `tests/test_config.py` cover invalid batches, nested contexts,
label priorities, and the compression of datasets created inside overrides.

PySHACL validation and IPython HTML display imports now occur at first use.
The fresh-process regression in `tests/test_startup.py` checks that ordinary
imports avoid these libraries, then exercises validation, HTML display, dataset
reading, default convention selection, and shared unit-registry identity.

Five sequential fresh-process samples on the same Windows/CPython 3.12.4
environment before and after this import change gave median process wall times
of **5.111 s** and **4.423 s**, respectively (about **13% lower**). Median time
inside the child around package import fell from **4.453 s** to **3.896 s**.
Both sets used isolated application directories and included five samples;
wall times include interpreter startup and exit cleanup. These local results
are indicative and do not establish a portable performance threshold. SHACL and
HTML display now pay their import cost on first use; their correctness is tested
separately. Required dependencies and public entry points are unchanged.

RDF graph-to-text serialization now has one internal implementation in
`ld/utils.py`. File methods, facade JSON-LD output, and metadata-file exporters
share context optimization and RDFLib formatting. Graph construction and each
entry point's URI validation remain at their original boundaries. The new local
`tests/ld/test_serialization.py` checks graph equivalence across these entry
points, all three structural/contextual modes, custom JSON-LD context, and the
existing difference in URI validation.

### Remaining work

The first modernization stage changed workspace organization and documentation.
The following are proposed follow-up steps, each suitable for independent,
verified commits. Public import paths, Python 3.10–3.13 support, HDF5 semantics,
and existing RDF behavior remain compatibility constraints.

| Maintenance area | Evidence and proposed change | Verification and completion criteria |
| --- | --- | --- |
| 1. Startup and import boundaries | Validation/display engines are now deferred. Scientific initialization, facade back-imports, and database package initialization remain candidates for profiling. Replace avoidable facade back-imports with imports from defining modules and defer further measured costs where initialization contracts allow it. | Repeat the startup protocol; check CLI help and first-use costs. Run startup, configuration, wrapper, convention, extension, representation, CLI, and SHACL tests. Preserve registry identity, exported symbols, convention activation, and registrations. Report measured improvements before setting a target. |
| 2. Serialization follow-up | Shared graph-to-text behavior has been consolidated. Review remaining argument normalization and graph-building duplication only where semantics agree. | Run `tests/ld/`, wrapper serialization tests, and `tests/test_cli.py`. Compare graph semantics and separately assert documented formatting. Preserve URI validation, `skipND`, prefixes, format aliases, and current `rdf_mappings` handling. |
| 4. Convention state isolation | Sequential nesting is corrected and characterized. Activation still mutates shared signatures/decoders, and partial activation failures lack a rollback contract. | Characterize failed signature insertion and define its rollback behavior separately. Settle per-file versus active-context semantics before concurrent-isolation changes; test actual decoding/signatures, not just pointer names. |
| 5. Compatibility shims and installation boundaries | Both `utils.py` and the `utils/` package exist; the package also re-exports split helpers. `utils.py` announces removal in 3.0. Audit actual callers and distribution contents before consolidating. | Run utility tests and import smoke checks from an installed wheel. Retain supported imports in 2.x. Check minimal installation and feature extras before proposing dependency changes. |
| 6. Contributor checks and CI | PR/push/manual checks exclude Zenodo write credentials and automatic cleanup. Artifact tests run in the matrix, and a dedicated server job enforces execution. Local checks and public-resource reads remain mixed. | Restore meaningful supported-version coverage for older integration tests and isolate local convention setup from connectivity probes. Verify actual Python/OS execution in hosted CI; keep skips visible. |

Two serialization differences need particular care: `ld.get_ld` accepts base
URIs ending in `#` or `/`, while the wrapper JSON-LD path has a stricter check;
contextual-only graph building currently ignores `rdf_mappings`. These are
existing behaviors, not instructions to silently normalize them during cleanup.

## Collaborative investigations

Before starting subagents, obtain the user's explicit approval for the topic,
purpose, agent count, and editing scope. Each approved investigation documents
its work in `.work/<topic>/`. Use separate reports for agents, with source
references, evidence, options, tradeoffs, checks, and open questions. Record the
discussion and final recommendation in a synthesis, preserving meaningful
disagreements and decision rationale. Assign separate report/code ownership to
avoid file conflicts, and review findings before implementing them. Keep accepted
decisions reflected in production documentation as well as the investigation.

## Local experiments

Existing unversioned ideas were moved to ignored `.playground/`, retaining their
relative paths. This includes the experimental LLM module and its tests; they
are not part of the active package architecture. A local archive manifest records
original paths and SHA-256 hashes. `AGENTS.md` and `.gitignore` stayed at the root.

The archive is local to this checkout and is not shipped or committed. New
production work should start from the tracked package and its tests. Consult
archived ideas only when a task explicitly calls for them.
