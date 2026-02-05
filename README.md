# HDF5 Research Data Management Toolbox

![Tests](https://github.com/matthiasprobst/h5RDMtoolbox/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/matthiasprobst/h5RDMtoolbox/graph/badge.svg?token=IVG4AQEW47)](https://codecov.io/gh/matthiasprobst/h5RDMtoolbox)
[![Documentation Status](https://readthedocs.org/projects/h5rdmtoolbox/badge/?version=latest)](https://h5rdmtoolbox.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/h5RDMtoolbox.svg)](https://badge.fury.io/py/h5RDMtoolbox)
![pyvers](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)

A Python package that helps researchers achieve sustainable 
[**FAIR (Findable, Accessible, Interoperable, Reusable)**](https://www.nature.com/articles/sdata201618) data management with HDF5 files. The toolbox provides a comprehensive
approach to the research data lifecycle through five main stages: **planning**, **collecting**, **analyzing**,
**sharing**, and **reusing** data.

> **Note**: This project is actively under development.




## ✨ Quick Start


One of the core features of the toolbox and success factors for achieving FAIR data, is using semantic metadata.

Let's see how we can use RDF (semantic metadata) together with HDF5 files using the toolbox:

```bash
# Install the package
pip install h5RDMtoolbox
```

```python
import h5rdmtoolbox as h5tbx
import rdflib
import numpy as np

# Create a new HDF5 file with semantic metadata
M4I = rdflib.Namespace("http://w3id.org/nfdi4ing/metadata4ing#")

# Create a new HDF5 file with FAIR metadata
with h5tbx.File("example.h5", "w") as h5:
    ds = h5.create_dataset("temperature", data=np.array([20, 21, 19, 22]))
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

The above saves three different serializations of the HDF5 content as RDF in Turtle (ttl) format.
The first one (`ttl_ctx`) is the **contextual** RDF serialization, which only includes the RDF triples that the user
has enriched the HDF5 file with. The second one (`ttl_struc`) is the **structural** RDF serialization, which includes 
all RDF triples that can be derived from the HDF5 file content. the third one (`ttl_full`) is the combination of the 
first two, which includes both the user enriched RDF triples and the RDF triples that can be derived from the HDF5 file 
content.

Below we show the first two serializations.

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

`ttl_ctx`:
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

[//]: # (The "HDF5 Research Data Management Toolbox" &#40;h5RDMtoolbox&#41; is a Python package supporting everybody who is working with)

[//]: # (HDF5 to achieve a sustainable data lifecycle which follows)

[//]: # (the [FAIR &#40;Findable, Accessible, Interoperable, Reusable&#41;]&#40;https://www.nature.com/articles/sdata201618&#41;)

[//]: # (principles. It specifically supports the five main steps of *planning*, *collecting*, *analyzing*, *sharing* and)

[//]: # (*reusing* data. Please visit the [documentation]&#40;https://h5rdmtoolbox.readthedocs.io/en/latest/&#41; for detailed)

[//]: # (information of try the [quickstart using colab]&#40;#quickstart&#41;.)


## 🚀 Key Features

- **🔗 HDF5 + [Xarray](https://docs.xarray.dev/en/stable/) Integration**: Seamless access to metadata during data analysis with native xarray support
- **🏷️ Persistent Identifiers**: Assign globally unique identifiers using RDF triples for FAIR compliance  
- **📋 Standardized Conventions**: Define and enforce community-specific metadata standards
- **☁️ Repository Integration**: Direct upload to Zenodo and other research repositories
- **🗄️ Database Support**: Use HDF5 files with MongoDB or native HDF5 databases
- **🔒 Semantic Enrichment**: Add RDF-based semantic meaning to your data
- **🌐 Catalog Integration**: Search and discover datasets through SPARQL-based catalogs


Find an example code in  [![In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/matthiasprobst/h5RDMtoolbox/blob/main/docs/colab/quickstart.ipynb) or check out the 
[📚 full Documentation](https://h5rdmtoolbox.readthedocs.io/en/latest/)

## Who is the package for?

For everybody, who is...

- ... looking for a management approach for his or her data.
- ... community has not yet established a stable convention.
- ... working with small and big data, that fits into HDF5 files.
- ... looking for an easy way to work with HDF5, especially
  through [Jupyter Notebooks](https://jupyterlab.readthedocs.io/en/stable/getting_started/installation.html).
- ... trying to integrate HDF5 with repositories and databases.
- ... wishing to enrich data semantically with the RDF standard.
- ... looking for a way to do all the above whiles not needing to learn a new syntax.
- ... new to HDF5 and wants to learn about it, especially with respect to the FAIR principles and data management.

## Who is it not for?

For everybody, who ...

- ... is looking for a management approach which at the same time allows high-performance and/or parallel work with HDF5
- ... has already well-established conventions and managements approaches in his or her community

## Package Architecture/structure

The toolbox implements six modules, which are shown below. The numbers reference to their main usage in the stages in
the data lifecycle shown [here](https://h5rdmtoolbox.readthedocs.io/en/latest/gettingstarted/index.html). The wrapper
module implements the main interface between the user and the HDF5 file. It
extends the features of the underlying `h5py` library. Some of the features are implemented in other modules, hence the
wrapper module depends on the convention, database and linked data (ld) module.

<a href="https://h5rdmtoolbox.readthedocs.io/en/latest/"><img src="docs/_static/h5tbx_modules.svg" alt="H5TBX modules" style="widht:600px;"></a>

Current implementation highlights in the modules:

- The **wrapper** module adds functionality on top of the `h5py` package. It allows to include so-called standard names,
  which are defined in conventions. And it implements interfaces, such as to the package `xarray`, which allows to carry
  metadata from HDF5 to the user. Other high-level interfaces like `.rdf` allows assigning semantic information to the
  HDF5 file.
- For the **database** module, `hdfDB` and `mongoDB` are implemented. The `hdfDB` module allows to use HDF5 files as a
  database. The `mongoDB` module allows to use mongoDB as a database by mapping the metadata of HDF5 files to the
  database.
- For the **repository** module, a Zenodo interface is implemented. Zenodo is a repository, which allows to upload and
  download data with a persistent identifier.
- For the **convention** module,
  the [standard attributes](https://h5rdmtoolbox.readthedocs.io/en/latest/conventions/standard_attributes_and_conventions.html)
  are implemented.
- The **layout** module allows to define expectations on the internal layout (object names, location, attributes,
  properties) of HDF5 files.
- The **catalog** module allows interfacing to HDF5 and RDF data published on Zenodo. Via a catalog file, a providers
  describe the data in various zenodo records they want to share. Through the catalog file, users can work with the
  data without downloading the full HDF5 files first.

## Quickstart

A quickstart notebook can be tested by clicking on the following badge:

[![Open Quickstart Notebook](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/matthiasprobst/h5RDMtoolbox/blob/main/docs/colab/quickstart.ipynb)

## Documentation

Please find a comprehensive documentation with many examples [here](https://h5rdmtoolbox.readthedocs.io/en/latest/) or
by click on the image, which shows the research data lifecycle in the center and the respective toolbox features on the
outside:

A paper is published in the journal [inggrid](https://preprints.inggrid.org/repository/view/23/).

## Installation

Use python 3.9 or higher (automatic testing is performed until 3.13). If you are a regular user, you can install the
package via pip:

    pip install h5RDMtoolbox

### Install from source:

Developers may clone the repository and install the package from source. Clone the repository first:

    git clone https://github.com/matthiasprobst/h5RDMtoolbox.git@main

Then, run

    pip install h5RDMtoolbox/

Add `--user` if you do not have root access.

For development installation run

    pip install -e h5RDMtoolbox/

### Dependencies

The core functionality depends on the following packages. Some of them are for general management others are very
specific to the features of the package:

**General dependencies are ...**

- `numpy`: Scientific computing, handling of arrays
- `matplotlib`: Plotting
- `appdirs`: Managing user and application directories
- `packaging`: Version handling
- `IPython`: Pretty display of data in notebooks
- `regex`: Working with regular expressions

**Specific to the package are ...**

- `h5py`: HDF5 file interface
- `xarray`: Working with scientific arrays in combination with attributes. Allows carrying metadata from HDF5
  to user
- `pint`: Allows working with units
- `pint_xarray`: Working with units for usage with xarray
- `python-forge`: Used to update function signatures when using
  the [standard attributes](https://h5rdmtoolbox.readthedocs.io/en/latest/conventions/standard_attributes_and_conventions.html)
- `pydantic`: Used to
  validate [standard attributes](https://h5rdmtoolbox.readthedocs.io/en/latest/conventions/standard_attributes_and_conventions.html)
- `pyyaml`: Reading and writing of yaml files, e.g. metadata definitions (conventions). Note, lower versions
  collide with python 3.11
- `requests`: Used to download files from the internet or validate URLs, e.g. metadata definitions (conventions)
- `rdflib`: Used to enable working with RDF
- `ontolutils`: Required to work with RDF and derive semantic description of HDF5 file content

#### Optional dependencies

To run unit tests or to enable certain features, additional dependencies must be installed.

Install optional dependencies by specifying them in square brackets after the package name, e.g.:

    pip install h5RDMtoolbox[mongodb]

[mongodb]

- `pymongo`: Database solution for HDF5 files

[csv]

- `pandas`: Mainly used for reading csv and pretty printing

[snt]

- `xmltodict`: Reading of xml files
- `tabulate`: Pretty printing of tables
- `python-gitlab`: Access to gitlab repositories
- `pypandoc`: Conversion of markdown files to html

## Citing the package

If you intend to use the package in your work, you may cite the software itself as published on paper in the
[Zenodo (latest version)](https://zenodo.org/records/13309253) repository. A related paper is published in the
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

## Contribution

Feel free to contribute. Make sure to write `docstrings` to your methods and classes and please write tests and use PEP
8 (https://peps.python.org/pep-0008/)

Please write tests for your code and put them into the `test/` folder. Visit the [README file](./tests/README.md) in the
test-folder for more information.

Pleas also add a jupyter notebook in the `docs/` folder in order to document your code. Please visit
the [README file](./docs/README.md) in the docs-folder for more information on how to compile the documentation.

Please use the **numpy style for the docstrings**:
https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html#example-numpy


