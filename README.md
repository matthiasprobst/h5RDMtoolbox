
<h1 text-align: center;><img src="docs/icons/icon4.svg" alt="" width="40"/> HDF5 Research Data Management Toolbox</h1>


![Tests](https://github.com/matthiasprobst/h5RDMtoolbox/actions/workflows/tests.yml/badge.svg)

*Note, that the repository is under current development! A first stable release is planned for 
Oktober, then being version 0.2.X.*

The "HDF5 Research Data Management Toolbox" (h5rdmtoolbox) supports the data creation, processing and sharing 
of data using the HDF5 file format while fulfilling the [FAIR](https://www.nature.com/articles/sdata201618) principles. 
So-called wrapper-classes serve as 
interfaces between the HDF5 files and the user and implement naming conventions, layout-defintions and 
provide helpful methods that facilitate processing and visualization. Special wrapper-classes can be written using class 
inheritance (some are already provided by the package), that further improve the bevahviour or restrict naming and/or 
data organization.

The package is divided into three sub-packages, each of which concerning a separate topic towards a FAIR 
data workflow. Note, that dependencies among the sub-packages exists, however a clear description for each 
sub-package can be found:
  - `conventions`: Naming standards mostly for attributes in the HDF5 files. Used by wrapper classes
  - `wrapper`: Implementaiton of wrapper classes: Interacting/working with HDF5 files including many useful features 
     and user-defined methods including static and dynamic layout definition
  - `database`: Practical and easy searching in multiple HDF5 files

The sub-packages are described in detail in the [documentation](https://matthiasprobst.github.io/h5RDMtoolbox/). 
`Jupyter Notebooks` as tutorials are provided in the respective documentation folder (/doc/<sub-package>).


## Installation
Navigate to the repository directory.

Clone the repository

     git clone https://github.com/matthiasprobst/h5RDMtoolbox

Make sure you have python3.8 or higher installed. Then run:

    pip h5RDMtoolbox
or for editable mode:

    pip -e h5RDMtoolbox

There are optional dependencies, e.g. for PIV-specific features. Specify them in square brackets after the package 
name. Check the setup config (`setup.cfg`) or the [documentation](https://matthiasprobst.github.io/h5RDMtoolbox/) for 
all optional dependencies. To install all dependencies, simply run

    pip h5RDMtoolbox[complete]


## Documentation
Documentation can be build following the README.md in the doc/ folder

## Testing
Go to the repository directory. For running all tests call

    cd h5RDMtoolbox
    pytest

To get a coverage report run (you need the package `pytest-cov`):

    pytest --cov --cov-report html
    
This will create a folder `covhtml/` with an `index.html` file in it.

Please request testdata from the author as long it is not shipped with the repo.

For a full test run in anaconda starting from cloning the repo, copy the following to your prompt:
```
git clone https://github.com/matthiasprobst/h5RDMtoolbox
conda create -n h5rdmtoolbox-tests -y python=3.8
conda activate h5rdmtoolbox-tests
pip install h5rdmtoolbox[complete]
pytest --cov --cov-report html
conda deactivate
conda env remove -n h5rdmtoolbox-tests
```

## Contribution
Feel free to contribute. Make sure to write `docstrings` to your methods and classes and please write 
tests and use PEP 8 (https://peps.python.org/pep-0008/)

Please use the **numpy style for the docstrings**: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html#example-numpy


