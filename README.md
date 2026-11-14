# HDF5 Research Data Management Toolbox

Scientific HDF5 access with xarray/Pint, RDF metadata, explicit SHACL validation,
local queries, catalogs, and Zenodo publication. This documentation describes the unreleased 3.0 API.
The latest release is 2.9.0; see the [migration guide](docs/migration-3.md) for API changes.

Python 3.15 compatibility is experimental. CI tests it separately; current
scientific dependencies may require source builds, including h5py.

Python 3.10 through 3.14 is supported. To use this development checkout:

```bash
python -m pip install -e .
```

Install `".[catalog]"` for catalog dependencies or `".[notebook]"` for notebook
display. `python -m pip install h5RDMtoolbox` installs the published release,
whose API differs from the development version documented here.

See [installation](docs/installation.md), the [user guide](docs/userguide/index.rst), [API reference](docs/api.rst),
and [documentation build instructions](docs/README.md).

## Scientific data and semantic metadata

```python
import h5rdmtoolbox as h5tbx
import rdflib
import numpy as np

# Create a new HDF5 file with semantic metadata
M4I = rdflib.Namespace("http://w3id.org/nfdi4ing/metadata4ing#")

# Create a new HDF5 file with FAIR metadata
with h5tbx.File("example.h5", "w") as h5:
    ds = h5.create_dataset("temperature", data=np.array([20, 21, 19, 22], dtype=np.int64))
    ds.attrs["units"] = h5tbx.Attribute(
        value="degree_Celsius",
        rdf_predicate=M4I.hasUnit,
        rdf_object="http://qudt.org/vocab/unit/DEG_C",
    )
    ds.attrs["description", "https://schema.org/description"] = "Room temperature measurements"

    ds_mean = h5.create_dataset("mean_temperature", data=np.mean(h5["temperature"][()]))
    ds_mean.attrs["units", M4I.hasUnit] = "degree_Celsius"
    ds_mean.rdf["units"].object = "http://qudt.org/vocab/unit/DEG_C"
    ds_mean.attrs["description", "https://schema.org/description"] = "Mean room temperature measurements"

    ds_mean.rdf.type = M4I.NumericalVariable
    ds_mean.rdf.data_predicate = M4I.hasNumericalValue

    ttl_ctx = h5.serialize("ttl", structural=False, contextual=True, file_uri="https://example.org#example.h5/")
    ttl_struc = h5.serialize("ttl", structural=True, contextual=False, file_uri="https://example.org#example.h5/")
    ttl_full = h5.serialize("ttl", file_uri="https://example.org#example.h5/")
```

The example produces three Turtle serializations. `ttl_ctx` contains semantic
annotations, `ttl_struc` describes HDF5 structure and metadata, and `ttl_full`
combines both views. The contextual and structural graphs are shown below.
RDF export can include dataset values; validation uses a separate metadata-only
default.

`ttl_ctx`:
```ttl
@prefix m4i: <http://w3id.org/nfdi4ing/metadata4ing#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org#example.h5/example.h5/mean_temperature> a m4i:NumericalVariable ;
    m4i:hasNumericalValue "20.5"^^xsd:float ;
    m4i:hasUnit <http://qudt.org/vocab/unit/DEG_C> ;
    schema:description "Mean room temperature measurements" .

<https://example.org#example.h5/example.h5/temperature> m4i:hasUnit <http://qudt.org/vocab/unit/DEG_C> ;
    schema:description "Room temperature measurements" .
```

`ttl_struc`:
```ttl
@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org#example.h5/example.h5> a hdf:File ;
    hdf:rootGroup <https://example.org#example.h5/example.h5/> .

hdf:H5T_IEEE_F64LE a hdf:Datatype .

hdf:H5T_INTEL_I64 a hdf:Datatype .

<https://example.org#example.h5/example.h5/> a hdf:Group ;
    hdf:member <https://example.org#example.h5/example.h5/mean_temperature>,
        <https://example.org#example.h5/example.h5/temperature> ;
    hdf:name "/" .

<https://example.org#example.h5/example.h5/mean_temperature> a hdf:Dataset ;
    hdf:attribute <https://example.org#example.h5/example.h5/mean_temperature@description>,
        <https://example.org#example.h5/example.h5/mean_temperature@units> ;
    hdf:dataspace <https://example.org#example.h5/example.h5/mean_temperature__dataspace> ;
    hdf:datatype hdf:H5T_FLOAT,
        hdf:H5T_IEEE_F64LE ;
    hdf:layout hdf:H5D_CONTIGUOUS ;
    hdf:maximumSize -1 ;
    hdf:name "/mean_temperature" ;
    hdf:rank 0 ;
    hdf:size 1 ;
    hdf:value 2.05e+01 .

<https://example.org#example.h5/example.h5/mean_temperature@description> a hdf:StringAttribute ;
    hdf:data "Mean room temperature measurements" ;
    hdf:name "description" .

<https://example.org#example.h5/example.h5/mean_temperature@units> a hdf:StringAttribute ;
    hdf:data "degree_Celsius" ;
    hdf:name "units" .

<https://example.org#example.h5/example.h5/mean_temperature__dataspace> a hdf:ScalarDataspace .

<https://example.org#example.h5/example.h5/temperature> a hdf:Dataset ;
    hdf:attribute <https://example.org#example.h5/example.h5/temperature@description>,
        <https://example.org#example.h5/example.h5/temperature@units> ;
    hdf:dataspace <https://example.org#example.h5/example.h5/temperature__dataspace> ;
    hdf:datatype hdf:H5T_INTEGER,
        hdf:H5T_INTEL_I64 ;
    hdf:layout hdf:H5D_CONTIGUOUS ;
    hdf:maximumSize 4 ;
    hdf:name "/temperature" ;
    hdf:rank 1 ;
    hdf:size 4 .

<https://example.org#example.h5/example.h5/temperature@description> a hdf:StringAttribute ;
    hdf:data "Room temperature measurements" ;
    hdf:name "description" .

<https://example.org#example.h5/example.h5/temperature@units> a hdf:StringAttribute ;
    hdf:data "degree_Celsius" ;
    hdf:name "units" .

<https://example.org#example.h5/example.h5/temperature__dataspace> a hdf:SimpleDataspace ;
    hdf:dimension <https://example.org#example.h5/example.h5/temperature__dataspace_dimension_0> .

<https://example.org#example.h5/example.h5/temperature__dataspace_dimension_0> a hdf:DataspaceDimension ;
    hdf:dimensionIndex 0 ;
    hdf:size 4 .
```

## Explicit validation

SHACL replaces conventions and the old layout engine. Writes accept ordinary
`attrs`; validation runs only when requested. By default it inspects structure
and metadata without reading dataset values. Set `include_scalar_values=True`
when scalar numerical values belong in the validation graph.

```python
from pathlib import Path
import rdflib
from h5rdmtoolbox.validation import validate

shapes = rdflib.Graph().parse(data='''
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix ex: <https://example.org/> .
ex:NamedDataset a sh:NodeShape; sh:targetClass hdf:Dataset;
    sh:property [sh:path hdf:name; sh:minCount 1] .
''', format="turtle")
result = validate(Path("example.h5"), shapes)
assert result.conforms
```

## Calibration and raw values

Reads return xarray data by default. Open with
`File("measurement.h5", decode_calibration=True)` to apply attached scale/offset
calibration. The setting belongs to that open file. `.values[...]` always reads
stored values. Units and coordinates remain available without conventions.

## Command line

Run `h5tbx ld dump example.h5` to print RDF, or write JSON-LD:

```bash
h5tbx ld dump example.h5 -o example.jsonld
```

## Scope and migration

Catalogs, local queries, SPARQL, and Zenodo publication remain supported.
Conventions, layouts, MongoDB, the HTTP server, Qt GUI, custom plotting,
vector/magnitude/normalization helpers, CSV/YAML constructors, and graph metrics
are removed. Use xarray, Pint, pandas, matplotlib, or RDFLib directly for those
analysis conveniences. See [the migration guide](docs/migration-3.md) and
[developer guide](docs/development.md).

## Citing the package

If you use the package in your work, cite the software using its version-specific
[Zenodo DOI for version 2.9.0](https://doi.org/10.5281/zenodo.24057487).
A related paper is published in the
journal [inggrid](https://www.inggrid.org/article/id/4028/). Thank you!

Alternatively or additionally, you can consult the `CITATION.cff` file.

Here is the BibTeX entry:

```
@article{probst2024h5rdmtoolbox,
	author = {Matthias Probst, Balazs Pritz},
	title = {h5RDMtoolbox - A Python Toolbox for FAIR Data Management around HDF5},
	volume = {2},
	year = {2024},
	url = {https://www.inggrid.org/article/id/4028/},
	issue = {1},
	doi = {10.48694/inggrid.4028},
	month = {8},
	keywords = {Data management,HDF5,metadata,data lifecycle,Python,database},
	issn = {2941-1300},
	publisher={Universitäts- und Landesbibliothek Darmstadt},
	journal = {ing.grid}
}
```

