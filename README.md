# HDF5 Research Data Management Toolbox

![Tests](https://github.com/matthiasprobst/h5RDMtoolbox/actions/workflows/tests.yml/badge.svg)
![DOCS](https://codecov.io/gh/matthiasprobst/h5RDMtoolbox/branch/dev/graph/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/h5rdmtoolbox/badge/?version=latest)](https://h5rdmtoolbox.readthedocs.io/en/latest/?badge=latest)
![pyvers](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)

*Note, that the project is still under development!*

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package supporting everybody who is working with
HDF5 to achieve a sustainable data lifecycle which follows
the [FAIR (Findable, Accessible, Interoperable, Reusable)](https://www.nature.com/articles/sdata201618)
principles. It specifically supports the five main steps of *planning*, *collecting*, *analyzing*, *sharing* and
*reusing* data. Please visit the [documentation](https://h5rdmtoolbox.readthedocs.io/en/latest/) for detailed
information of try the [quickstart using colab](#quickstart).

## Highlights

- Combining HDF5 and [xarray](https://docs.xarray.dev/en/stable/) to allow easy access to metadata and data during
  analysis and processing (
  see [here](https://h5rdmtoolbox.readthedocs.io/en/latest/gettingstarted/quickoverview.html#datasets-xarray-interface).
- Assigning [metadata with "globally unique and persistent identifiers"]() as required
  by [F1 of the FAIR principles](https://www.go-fair.org/fair-principles/f1-meta-data-assigned-globally-unique-persistent-identifiers/)
  . This "remove[s] ambiguity in the meaning of your published data...".
- Define standard attributes through
  [conventions](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/convention/index.html) and enforce users to use
  them
- Upload HDF5 files directly
  to [repositories](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/repository/index.html)
  like [Zenodo](https://zenodo.org/)
  or [use them with noSQL databases](https://h5rdmtoolbox.readthedocs.io/en/latest/userguide/database/index.html) like
  [mongoDB](https://www.mongodb.com/).

## Who is the package for?

For everybody, who is...

- ... looking for a management approach for his or her data
- ... community has not yet established a stable convention
- ... working with small and big data, that fits into HDF5 files
- ... looking for an easy way to work with HDF5, especially through Jupyter Notebooks
- ... looking to integrate HDF5 with repositories and databases
- ... looking for a way to do all the above whiles not needing to learn a new syntax
- ... new to HDF5 and wants to learn about it, especially with respect to the FAIR principles and data management

## Who is it not for?

For everybody, who ...

- ... is looking for a management approach which at the same time allows high-performance and/or parallel work with HDF5
- ... has established conventions and managements approaches in his or her community

## Package Architecture/structure

The toolbox implements five modules, which are shown below. The numbers reference to their main usage in the stages in
the data lifecycle above. Except the wrapper module, which uses the convention module, all other modules are independent
of each other.

<a href="https://h5rdmtoolbox.readthedocs.io/en/latest/"><img src="docs/_static/h5tbx_modules.svg" alt="H5TBX modules" style="widht:600px;"></a>

Current implementation highlights in the modules:

- The **wrapper** module adds functionality on top of the `h5py` package. It allows to include so-called standard names,
  which are defined in conventions. And it implements an interface with the package `xarray`, which allows to carry
  metadata from HDF5 to the user.
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

## Quickstart

A quickstart notebook can be tested by clicking on the following badge:

[![Open Quickstart Notebook](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/matthiasprobst/h5RDMtoolbox/blob/main/docs/colab/quickstart.ipynb)

## Documentation

Please find a comprehensive documentation with many examples [here](https://h5rdmtoolbox.readthedocs.io/en/latest/) or
by click on the image, which shows the research data lifecycle in the center and the respective toolbox features on the
outside:

A paper is published in the journal [inggrid](https://preprints.inggrid.org/repository/view/23/).

## Installation

Use python 3.8 or higher (automatic testing is performed until 3.12). If you are a regular user, you can install the
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

- `numpy>=1.20`: Scientific computing, handling of arrays
- `matplotlib>=3.5.2`: Plotting
- `appdirs>=1.4.4`: Managing user and application directories
- `packaging`: Version handling
- `IPython>=8.4.0`: Pretty display of data in notebooks
- `regex>=2020.7.9`: Working with regular expressions

**Specific to the package are ...**

- `h5py=3.7.0`: HDF5 file interface
- `xarray>=2022.3.0`: Working with scientific arrays in combination with attributes. Allows carrying metadata from HDF5
  to user
- `pint>=0.19.2`: Allows working with units
- `pint_xarray>=0.2.1`: Working with units for usage with xarray
- `python-forge==18.6.0`: Used to update function signatures when using
  the [standard attributes](https://h5rdmtoolbox.readthedocs.io/en/latest/conventions/standard_attributes_and_conventions.html)
- `pyyaml>6.0.0`: Reading and writing of yaml files, e.g. metadata definitions (conventions). Note, lower versions
  collide with python 3.11
- `requests`: Used to download files from the internet or validate URLs, e.g. metadata definitions (conventions)

#### Optional dependencies

To run unit tests or to enable certain features, additional dependencies must be installed.

Install optional dependencies by specifying them in square brackets after the package name, e.g.:

    pip install h5RDMtoolbox[mongodb]

[mongodb]

- `pymongo>=4.2.0`: Database solution for HDF5 files

[csv]

- `pandas>=1.4.3`: Mainly used for reading csv and pretty printing

[snt]

- `xmltodict`: Reading of xml files
- `tabulate>=0.8.10`: Pretty printing of tables
- `python-gitlab`: Access to gitlab repositories
- `pypandoc>=2.3`: Conversion of markdown files to html

## Planned, future developments

- Using JSON schema definitions for layouts and conventions

## Citing the package

If you intend to use the package in your work, you may cite the paper in the
journal [inggrid](https://preprints.inggrid.org/repository/view/23/)

Here's the bibtext to it:

```
@article{probst2023h5rdmtoolbox,
  title={h5RDMtoolbox-A Python Toolbox for FAIR Data Management around HDF5},
  author={Probst, Matthias and Pritz, Balazs},
  year={2023},
  publisher={ing. grid Preprint Repository}
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


