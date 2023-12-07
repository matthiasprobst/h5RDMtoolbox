# HDF5 Research Data Management Toolbox

![Tests](https://github.com/matthiasprobst/h5RDMtoolbox/actions/workflows/tests.yml/badge.svg)
![DOCS](https://codecov.io/gh/matthiasprobst/h5RDMtoolbox/branch/dev/graph/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/h5rdmtoolbox/badge/?version=latest)](https://h5rdmtoolbox.readthedocs.io/en/latest/?badge=latest)
![pyvers](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)

*Note, that the project is still under development!*

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package supporting everybody who is working with
HDF5 to achieve a sustainable data lifecycle which follows
the [FAIR (Findable, Accessible, Interoperable, Reusable)](https://www.nature.com/articles/sdata201618)
principles. It specifically supports the five main steps of

1. Planning (defining a internal layout for HDF5 a metadata convention for attribute usage)
2. Collecting data (creating HDF5 files or converting to HDF5 files from other sources)
3. Analyzing and processing data (Plotting, deriving data, ...)
4. Sharing data (publishing, archiving, ... e.g. to databases like [mongoDB](https://www.mongodb.com/) or repositories
   like [Zenodo](https://zenodo.org/))
5. Reusing data (Searching data in databases, local file structures or online repositories
   like [Zenodo](https://zenodo.org)).

## Quickstart

A quickstart notebook can be tested by clicking on the following badge:

[![Open Quickstart Notebook](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/matthiasprobst/h5RDMtoolbox/blob/main/docs/colab/quickstart.ipynb)

## Documentation

Please find a comprehensive documentation with many examples [here](https://h5rdmtoolbox.readthedocs.io/en/latest/) or by click
on the image, which shows the research data lifecycle in the center and the respective toolbox features on the outside:

A paper is published in the journal [inggrid](https://preprints.inggrid.org/repository/view/23/).

<a href="https://h5rdmtoolbox.readthedocs.io/en/latest/"><img src="docs/_static/new_icon_with_text.svg" alt="RDM lifecycle" style="widht:600px;"></a>

## Installation

Use python 3.8 or higher (tested until 3.10). If you are a regular user, you can install the package via pip:

    pip install h5RDMtoolbox

### Install from source:

Developers may clone the repository and install the package from source. Clone the repository first:

    git clone https://github.com/matthiasprobst/h5RDMtoolbox.git

Then, run

    pip install h5RDMtoolbox/

Add `--user` if you do not have root access.

For development installation run

    pip install -e h5RDMtoolbox/

### Dependencies

The core functionality depends on the following packages. Some of them are for general management others are very
specific to the features of the package:

**General dependencies are ...**

- `numpy>=1.20,<1.23.0`: Scientific computing, handling of arrays
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
- `pyyaml`: Reading and writing of yaml files, e.g. metadata definitions (conventions)
- `requests`: Used to download files from the internet or validate URLs, e.g. metadata definitions (conventions)

#### Optional dependencies

To run unit tests or to enable certain features, additional dependencies must be installed.

Install optional dependencies by specifying them in square brackets after the package name, e.g.:

    pip install h5RDMtoolbox[mongodb]

[mongodb]

- `pymongo>=4.2.0`: Database solution for HDF5 files

[io]

- `pco_tools>=1.0.0`: Reading of pco image files
- `opencv-python>=4.5.3.56`: Reading of image files (other than pco)
- `pandas>=1.4.3`: Mainly used for reading csv and pretty printing

[snt]

- `xmltodict`: Reading of xml files
- `tabulate>=0.8.10`: Pretty printing of tables
- `python-gitlab`: Access to gitlab repositories
- `pandoc>=2.3`: Conversion of markdown files to html

## Planned, future developments

- Using JSON schema definitions for layouts and conventions

## Citing the package
If you intend to use the package in your work, you may cite the paper in the journal [inggrid](https://preprints.inggrid.org/repository/view/23/)

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


