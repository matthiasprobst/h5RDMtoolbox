Research Data Management Toobox Documentation
=============================================

Overview
--------

The HDF5 Research DataManagement Toolbox (h5RDMtoolbox) supports the data creation, processing and sharing
of data using the HDF5 file format while fullfilling the [FAIR](https://www.nature.com/articles/sdata201618) principles.

*Note, that the repository is under current development!*

The packges comes with four sub-packages:
  - `meta_convention`: Naming standards mostly for attributes in the HDF5 files
  - `h5wrapper`: Interacting/working with HDF5 files including many useful features and user-defined methods including static and dynamic layout definition
  - `x2hdf`: package facilitating conversion processes to meet the layout requirements defined in `h5wrapperpy`
  - `h5database`: Practical and easy searching in multiple HDF5 files


Installation
------------
Install from source from github:

.. code:: sh

   python -m pip install git+https://git.scc.kit.edu/da4323/h5RDMtoolbox.git

Install from downloaded copy:

.. code:: sh

   git clone https://git.scc.kit.edu/da4323/h5RDMtoolbox.git
   python3.8 -m pip install h5RDMtoolbox/


.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: h5wrapper

   Overview <h5wrapper/overview>
   Notebook Tutorials <h5wrapper/tutorials>

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: x2hdf

   Notebook Tutorials <x2hdf/tutorials>

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: h5database

   Notebook Tutorials <h5database/tutorials>

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: conventions

   Notebook Tutorials <conventions/tutorials>

Installation
------------
Install from source from github:

.. code:: sh

   python -m pip install git+https://git.scc.kit.edu/da4323/h5RDMtoolbox.git

Install from downloaded copy:

.. code:: sh

   git clone https://git.scc.kit.edu/da4323/h5RDMtoolbox.git
   python -m pip install .h5RDMtoolbox