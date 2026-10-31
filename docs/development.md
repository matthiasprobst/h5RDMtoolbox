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

The latest full coverage run on Windows/CPython 3.12.4 after the test-isolation
changes produced **444 passed, 27 skipped, and no failures**. Live uploads and
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

## Prioritized maintenance backlog

The two-agent review and parent verification are recorded in
`.work/architecture-quality/README.md`, with separate architecture and quality
reports. They identified additional correctness gaps that the editable-install
test suite does not expose: automatic account-wide Sandbox cleanup in CI,
missing installed metadata/resources, and same-instance Convention restoration.
Contain default CI writes and repair installed metadata before undertaking a
larger concurrency redesign. The reports include evidence, alternatives, and
acceptance checks; their baseline findings are not claims that these gaps have
already been fixed.

The pinned Sphinx 8 documentation environment requires Python 3.10+, independently
of the base package's Python 3.9 support.

### Completed refactorings

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
verified commits. Public import paths, Python 3.9–3.13 support, HDF5 semantics,
and existing RDF behavior remain compatibility constraints.

| Maintenance area | Evidence and proposed change | Verification and completion criteria |
| --- | --- | --- |
| 1. Startup and import boundaries | Validation/display engines are now deferred. Scientific initialization, facade back-imports, and database package initialization remain candidates for profiling. Replace avoidable facade back-imports with imports from defining modules and defer further measured costs where initialization contracts allow it. | Repeat the startup protocol; check CLI help and first-use costs. Run startup, configuration, wrapper, convention, extension, representation, CLI, and SHACL tests. Preserve registry identity, exported symbols, convention activation, and registrations. Report measured improvements before setting a target. |
| 2. Serialization follow-up | Shared graph-to-text behavior has been consolidated. Review remaining argument normalization and graph-building duplication only where semantics agree. | Run `tests/ld/`, wrapper serialization tests, and `tests/test_cli.py`. Compare graph semantics and separately assert documented formatting. Preserve URI validation, `skipND`, prefixes, format aliases, and current `rdf_mappings` handling. |
| 3. Decoder correctness | Configuration validation and format restoration have been corrected. Decoder cleanup still contains adjacent `'DATA_SCALE' 'DATA_OFFSET'` literals. Address this with an explicit regression test in a separate behavior-fix commit. | Assert decoder output attributes in wrapper tests. Keep behavior changes separate from serialization and import refactors. |
| 4. Convention state isolation | `convention/cfg.py` has a context-local pointer, while `convention/core.py` mutates signatures and `wrapper/ds_decoder.py` keeps global decoder selection. Define the supported concurrency contract before changing storage. | Start with nested convention and decoder restoration tests. If task/thread isolation becomes a goal, add concurrent tests that exercise different conventions and signatures; do not infer isolation from `ContextVar` alone. |
| 5. Compatibility shims and installation boundaries | Both `utils.py` and the `utils/` package exist; the package also re-exports split helpers. `utils.py` announces removal in 3.0. Audit actual callers and distribution contents before consolidating. | Run utility tests and import smoke checks from an installed wheel. Retain supported imports in 2.x. Check minimal installation and feature extras before proposing dependency changes. |
| 6. Contributor checks and CI | The testing guide is current and live uploads are opt-in. The test workflow still triggers on pushes only; local checks and external-service reads remain mixed. | Add pull-request coverage with an explicit credential/service policy and a discoverable local test selection. Verify Python/OS coverage and make missing integrations visible rather than treating skipped tests as coverage. |

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
