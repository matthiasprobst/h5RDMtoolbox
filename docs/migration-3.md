# Migrating to the 3.0 API

Existing HDF5 data and RDF annotations stay readable. Python APIs deliberately
change; release metadata remains at 2.9.0 during implementation.

## Metadata and validation

Remove `use(...)`, `Convention`, standard-attribute registration and dynamically
injected creation keywords. Supply metadata through `attrs={"units": "m"}` or
`dataset.attrs["units"] = "m"`. Units are interpreted during scientific operations;
writing metadata no longer invokes a convention validator.

Replace `Layout` specifications with SHACL files. Use
`validation.validate(path, shapes_path)` explicitly after preparing data.
Required names/counts, ranks/dimensions, datatypes, compression and metadata map
to structural RDF constraints. Arbitrary Python validation callbacks need manual
migration; numerical array analysis belongs in scientific analysis code.
Validation does not modify files or enforce checks during writes or publication.

## Scientific reads

`dataset[...]` returns xarray values with coordinates and metadata.
`dataset.values[...]` returns stored NumPy values. Replace convention-selected
scale/offset decoding with `File(path, decode_calibration=True)`; default is False.
The option is local to the open file, including its child objects and lazy results.
Custom data transformations can operate directly on the returned xarray object.

## Removed features

The HTTP server, Qt GUI, MongoDB adapter, graph metrics/visualization, custom
plotting, vector/magnitude/normalization accessors and CSV/YAML constructors are
removed. Use pandas for CSV, ordinary HDF5 creation calls for construction,
xarray/Pint for analysis, and matplotlib/RDFLib for visualization and metrics.
Local HDF5 queries, SPARQL, catalogs and Zenodo publication remain available.
Old releases remain accessible at the v2.9.0 tag.

## Initialization and installation

Imports no longer create application directories or clean caches. Directory
creation and cache cleanup happen explicitly. Notebook display uses the optional
`notebook` extra; catalog dependencies use `catalog`. Global plotting options and
convention configuration keys are removed. The source package lives under src;
install the editable project before running examples or tests.
