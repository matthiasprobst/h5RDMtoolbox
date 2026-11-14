# Development

The 3.0 implementation targets scientific HDF5 I/O, RDF, explicit SHACL validation,
local discovery, catalogs, and Zenodo publication. The version remains 2.9.0 until
the user supplies a reserved version-specific 3.0 DOI.

## Dependency boundaries

The public facade imports features on first use. Scientific I/O wraps h5py and
uses xarray/Pint for coordinates and units. RDF extraction operates on h5py
objects independently of validation. SHACL validation consumes graphs; catalog
validation shares that engine. Publication and network clients load on request.
Lower-level modules import defining modules rather than the package facade.

No ordinary import creates directories, deletes caches, starts network requests,
or configures application logging. Application directories are created on explicit
use; cache cleanup is explicit. Calibration is selected per open file with
`decode_calibration=False` by default and is preserved by lazy query results.

## Validation and storage contracts

Use `validation.validate(source, shapes)` with paths, open files, or RDF graphs.
The default graph contains structure and metadata, without dataset payload reads.
Scalar values are explicit opt-in. Shape files use standard SHACL; there is no
convention registry or layout rule engine. Invalid input raises an exception;
nonconformance returns a report. Existing RDF annotation attributes, literal
lexical forms, language tags and datatypes remain readable without migration.

## Checks

```bash
python -m pip install -e ".[test,docs]"
python -m pytest --cov=h5rdmtoolbox --cov-report=html
python -m pylint src/h5rdmtoolbox --rcfile=.pylintrc
python -m sphinx -b html -D nb_execution_mode=off docs docs/_build/html
```

Tests isolate application directories. Zenodo uploads require both explicit
`H5RDMTOOLBOX_RUN_ZENODO_UPLOAD_TESTS=1` and `ZENODO_SANDBOX_API_TOKEN`.
Public-resource reads may occur in integration tests; the full suite is not
universally offline. CI uses read-only permissions and no Zenodo write tokens.
Distribution tests build an sdist and wheel and exercise the installed artifact.

Measure import/CLI startup, first read, slicing, RDF, SHACL and catalog indexing
against v2.9.0 with matched interpreter and dependencies. Use nine repeated
samples and report medians, first-use costs and peak memory separately. The
acceptance targets are 20% lower startup time and at most 10% slowdown in retained
workloads. Timing results belong with the validation evidence, not assumptions.
See [the current measurements and remaining performance gate](verification-3.md).

## DOI-first release checklist

Obtain a reserved version-specific DOI before changing the version. Update
pyproject.toml, CITATION.cff, root codemeta.json, Colab pin, changelog and README
citation together. Runtime version comes from installed metadata. Refresh the
editable install and verify built distributions. Never run .build.bat during
preparation: it uploads immediately. Tags and publication require separate
instructions. The current reserved 2.9.0 DOI must not be reused for 3.0.0.

Historical 2.x architecture and audit evidence is retained in
`docs/history/development-2.md` in the repository.

## Source map

- `src/h5rdmtoolbox/wrapper/`: separate file, group, dataset and attribute modules;
  `core` only re-exports the object classes.
- `science/`: xarray I/O, Pint unit conversion and calibration.
- `ld/`: RDF annotations and structural/contextual graph extraction.
- `validation/`: the shared explicit SHACL service and report types.
- `database/`: local HDF5 searches, SPARQL and lazy query results (no MongoDB).
- `catalog/`, `repository/`: discovery stores and Zenodo publication.
- `src/h5rdmtoolbox_cli.py`: lightweight command-line dispatch.

These names retain familiar public entry points while making implementation
responsibilities explicit. Tests mirror the retained areas.
