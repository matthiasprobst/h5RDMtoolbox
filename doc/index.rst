.. image:: icons/icon4_header.svg
  :width: 500
  :alt: Alternative text



Overview
========

The HDF5 Research Data Management Toolbox (h5RDMtoolbox) supports the data creation, processing and sharing
of data using the HDF5 file format while fulfilling the `FAIR priciples <https://www.nature.com/articles/sdata201618>`_.


.. note::

   This project is under current development!


The packges comes with four sub-packages:
  - :doc:`conventions/index`: Naming standards mostly for attributes in the HDF5 files
  - :doc:`h5wrapper/index`: Interacting/working with HDF5 files including many useful features and user-defined methods including static and dynamic layout definition
  - :doc:`x2hdf/index`: package facilitating conversion processes to meet the layout requirements defined in `h5wrapperpy`
  - :doc:`h5database/index`: Practical and easy searching in multiple HDF5 files

.. image:: icons/icon4_subpackages.svg
  :width: 300
  :alt: Alternative text
  :align: center

Installation
------------
The repository requires python 3.8. or higher.

Install from source from github:

.. code:: sh

   python3.8 -m pip install git+https://git.scc.kit.edu/da4323/h5RDMtoolbox.git

Clone and install from source:

.. code:: sh

   git clone https://git.scc.kit.edu/da4323/h5RDMtoolbox.git
   python3.8 -m pip install h5RDMtoolbox/

You may install optional dependencies:

.. code:: sh

   python3.8 -m pip install "h5RDMtoolbox[vtk]"  # installs dependencies to convert datasets to vtk
   python3.8 -m pip install "h5RDMtoolbox[tec]"  # installs pytecplot to build tecplot-readable HDF5 files
   python3.8 -m pip install "h5RDMtoolbox[piv]"  # installs e.g. netCDF4 which isneeded to convt n files
   python3.8 -m pip install "h5RDMtoolbox[cfd]"  # installs dependencies needed by the cfd2hdf package
   python3.8 -m pip install "h5RDMtoolbox[complete]"  # installs all avbove plus dependencies for testing and documentation




.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    Conventions <conventions/index>
    H5wrapper <h5wrapper/index>
    x2hdf <x2hdf/index>
    H5Database <h5database/index>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

