# HDF5 Research Data Management Toolbox

*Note, that the repository is under current development!*

The "HDF5 Research Data Management Toolbox" (h5rdmtoolbox) supports the data creation, processing and sharing 
of data using the HDF5 file format while fullfilling the [FAIR](https://www.nature.com/articles/sdata201618) principles.
The core idea is to make use of the popular file format HDF5. So-called wrapper-classes serve as 
interfaces between the file and the user and implement naming conventions, layout-defintions and 
provide helpful methods that facilitate processing and visualization. Special wrapper-classes can be written using class 
inheritance (some are already provided by the package), that further improve the bevahviour or restrict naming and/or 
data organization.

The package is divided into four sub-packages, each of which concerning a separate topic towards a FAIR 
data workflow. Note, that dependencies among the sub-packages exists, however a clear description for each 
sub-package can be found:
  - `conventions`: Naming standards mostly for attributes in the HDF5 files. Used by wrapper classes
  - `h5wrapper`: Implementaiton of wrapper classes: Interacting/working with HDF5 files including many useful features 
     and user-defined methods including static and dynamic layout definition
  - `x2hdf`: package facilitating conversion processes to meet the layout requirements defined in `h5wrapperpy`
  - `h5database`: Practical and easy searching in multiple HDF5 files

The sub-packages are described in detail in the [documentation](./doc/_build/index.html). 
`Jupyter Notebooks` as tutorials are provided in the respective documentation folder (/doc/<sub-package>).


## Installation
For development:

    python3.8 -m pip install -e .
otherwise

    python3.8 -m pip install .

To only install special functionality, e.g. only vtk support in addition to core dependendies, run:

    pip install "h5rdmtoolbox[vtk]"

**Note**: There are some optional packages that are not listed in the requirements, which 
you have to install yourself:
1. `numba`: For code acceleration of heavy computations (`pip install numba`)
2. `pytecplot`: For interfacing with TecPlot (`pip install pytecplot`). Require license for TecPlot!

## Documentation
Documentation can be build following the README.md in the doc/ folder

## Testing
Go to the repository directory. For running all tests call
```
pytest
```
To get a coverage report run (you need the package `pytest-cov`):
```
pytest --cov --cov-report html
```
This will create a folder `covhtml/` with an `index.html` file in it.

You may also copy the following into your anaconda prompt:
```
conda create -n h5rdmtoolbox-tests python=3.8
conda activate h5rdmtoolbox-tests
pip install -e .
pytest h5rdmtoolbox
conda deactivate
```

## Contribution
Feel free to contribute. Make sure to write `docstrings` to your methods and classes and please write 
tests and use PEP 8 (https://peps.python.org/pep-0008/)

Please use the **numpy style for the docstrings**: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html#example-numpy


