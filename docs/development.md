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
| `utils/`, `_cfg.py`, `user.py`, `_repr.py` | Shared file/network/HDF5 helpers, mutable configuration and unit registry, application directories, and text/notebook representations. Some still import back through the facade. |
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
the wrapper imports RDF support, convention code imports wrapper decoders, and
utility code reads facade exports. Refactors must account for the actual import
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
  The SHACL module imports PySHACL eagerly, while representations import
  IPython display support.
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

For prose and navigation, build without notebook execution:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html
```

The pre-change documentation baseline built successfully without Sphinx warnings
with notebook execution disabled. Notebook edits require a separate build using
the configured execution policy. The historical `tests/README.md` contains old
setup instructions; use `pyproject.toml` and the root agent guidelines for the
supported Python versions and current commands.

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

### Completed refactorings

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

| Order | Evidence and proposed change | Verification and completion criteria |
| --- | --- | --- |
| 1. Startup and import boundaries | The facade eagerly reaches scientific, display, validation, and database code. Start by replacing avoidable facade back-imports with imports from defining modules, then defer measured costly feature imports where initialization contracts allow it. Keep the CLI's existing command-local imports. | Repeat the startup protocol; check CLI help and first-use costs. Run configuration, wrapper, convention, extension, representation, CLI, and SHACL tests. Preserve registry identity, exported symbols, convention activation, and registrations. Report the actual improvement before setting a target. |
| 2. Serialization follow-up | Shared graph-to-text behavior has been consolidated. Review remaining argument normalization and graph-building duplication only where semantics agree. | Run `tests/ld/`, wrapper serialization tests, and `tests/test_cli.py`. Compare graph semantics and separately assert documented formatting. Preserve URI validation, `skipND`, prefixes, format aliases, and current `rdf_mappings` handling. |
| 3. Small correctness fixes | `_cfg.py` validates plotting-name order using list truthiness and rejects `None` compression values despite `None` defaults. Decoder cleanup contains adjacent `'DATA_SCALE' 'DATA_OFFSET'` literals. Address each with an explicit regression test in a separate behavior-fix commit. | Add valid/invalid configuration cases to `tests/test_config.py` and assert decoder output attributes in wrapper tests. Do not combine these behavior changes with serialization or import refactors. |
| 4. Convention state isolation | `convention/cfg.py` has a context-local pointer, while `convention/core.py` mutates signatures and `wrapper/ds_decoder.py` keeps global decoder selection. Define the supported concurrency contract before changing storage. | Start with nested convention and decoder restoration tests. If task/thread isolation becomes a goal, add concurrent tests that exercise different conventions and signatures; do not infer isolation from `ContextVar` alone. |
| 5. Compatibility shims and installation boundaries | Both `utils.py` and the `utils/` package exist; the package also re-exports split helpers. `utils.py` announces removal in 3.0. Audit actual callers and distribution contents before consolidating. | Run utility tests and import smoke checks from an installed wheel. Retain supported imports in 2.x. Check minimal installation and feature extras before proposing dependency changes. |
| 6. Contributor checks and CI | `tests/README.md` still describes Python 3.8, and the test workflow currently triggers on pushes only. Local and external-service checks are mixed. | Update the old guide; add pull-request coverage with an explicit credential/service policy and a discoverable local test selection. Verify Python/OS coverage and make missing integrations visible rather than treating skipped tests as coverage. |

Two serialization differences need particular care: `ld.get_ld` accepts base
URIs ending in `#` or `/`, while the wrapper JSON-LD path has a stricter check;
contextual-only graph building currently ignores `rdf_mappings`. These are
existing behaviors, not instructions to silently normalize them during cleanup.

## Local experiments

Existing unversioned ideas were moved to ignored `.playground/`, retaining their
relative paths. This includes the experimental LLM module and its tests; they
are not part of the active package architecture. A local archive manifest records
original paths and SHA-256 hashes. `AGENTS.md` and `.gitignore` stayed at the root.

The archive is local to this checkout and is not shipped or committed. New
production work should start from the tracked package and its tests. Consult
archived ideas only when a task explicitly calls for them.
