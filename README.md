<h1 text-align: center;><img src="docs/icons/icon4.svg" alt="" width="40"/> HDF5 Research Data Management Toolbox</h1>


![Tests](https://github.com/matthiasprobst/h5RDMtoolbox/actions/workflows/tests.yml/badge.svg)
![DOCS](https://codecov.io/gh/matthiasprobst/h5RDMtoolbox/branch/dev/graph/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/h5rdmtoolbox/badge/?version=latest)](https://h5rdmtoolbox.readthedocs.io/en/latest/?badge=latest)

*Note, that the project is still beta!*

The "HDF5 Research Data Management Toolbox" (`h5RDMtoolbox`) is a python package that provides a set of tools to work
with HDF5 files. It is designed to be used in research and development projects. It supports the data creation,
processing and sharing of data using the HDF5 file format pursuing the
[FAIR](https://www.nature.com/articles/sdata201618) principles.

All functionalities are wrapped around the [`h5py` package](https://www.h5py.org/). Flexible, user-defined conventions,
which are standardized attributes and file layout specifications achieve the goals of sustainable data management.

By including other packages such as `xarray`, visualization of data becomes fast and easy. Also, a database-solution for
HDF5 files is provided.

## Documentation

Please find the comprehensive documentation with examples [here](h5rdmtoolbox.readthedocs.io/en/latest/).

## Installation

Use python 3.8 or higher (tested until 3.10).

Install from website:

    pip install git+https://github.com/matthiasprobst/h5RDMtoolbox

For **development**, clone the repository and install it in editable mode:

    git clone https://github.com/matthiasprobst/h5RDMtoolbox
    pip install -e h5RDMtoolbox

There are optional dependencies, that can be installed to enable additional features. They are listed in 
the next section.

### Requirements/Dependencies

- appdirs>=1.4.4: Managing user and application directories
- numpy>=1.20,<1.23.0: Scientific computing, handling of arrays
- h5py>=3.7.0: HDF5 file interface
- matplotlib>=3.5.2: Plotting
- pandas>=1.4.3: Mainly used for reading csv and pretty printing
- IPython>=8.4.0: Pretty display of data in notebooks
- pyyaml: Reading and writing of yaml files
- xarray>=2022.3.0: Working with scientific arrays in combination with attributes
- pint>=0.19.2: Working with units
- pint_xarray>=0.2.1: Working with units in xarray
- regex>=2020.7.9: Regular expressions
- packaging: Version handling
- python-forge==18.6.0: Used to update function signatures when using the h5rdmtoolbox conventions
- requests: Used to download files from the internet

#### Optional dependencies

Install optional dependencies by specifying them in square brackets after the package name, e.g.:

    pip install h5RDMtoolbox[mongodb]
    
    

[mongodb]
- pymongo>=4.2.0: Database solution for HDF5 files

[io]

- pco_tools>=1.0.0: Reading of pco image files
- opencv-python>=4.5.3.56: Reading of image files (other than pco)

[snt]
- pooch: Downloading of files from the internet
- xmltodict: Reading of xml files
- tabulate>=0.8.10: Pretty printing of tables
- python-gitlab: Access to gitlab repositories

## Contribution

Feel free to contribute. Make sure to write `docstrings` to your methods and classes and please write tests and use PEP
8 (https://peps.python.org/pep-0008/)

Please use the **numpy style for the docstrings**:
https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html#example-numpy


