.. image:: icons/icon4_header.svg
  :width: 500
  :alt: Alternative text



Overview
========

The HDF5 Research Data Management Toolbox (h5RDMtoolbox) supports the data creation, processing and sharing
of data using the HDF5 file format pursuing the `FAIR priciples <https://www.nature.com/articles/sdata201618>`_.


.. note::

   This project is under current development! The first stable release is expected for Oktober 2022.


The packges comes with three sub-packages:
  - :doc:`convention <conventions/index>`: Naming standards mostly for attributes in the HDF5 files
  - :doc:`wrapper <wrapper/index>`: Interacting/working with HDF5 files including many useful features and user-defined methods including static and dynamic layout definition
  - :doc:`database <database/index>`: Practical and easy searching in multiple HDF5 files

.. image:: icons/package_overview.svg
  :width: 350
  :alt: Alternative text
  :align: center

Installation
------------
The repository requires python 3.8. or higher (tested for 3.8 and 3.9).

Install from source from github:

.. code:: sh

   python3.8 -m pip install https://github.com/matthiasprobst/h5RDMtoolbox

Clone and install from source:

.. code:: sh

   git clone https://github.com/matthiasprobst/h5RDMtoolbox
   python3.8 -m pip install h5RDMtoolbox/

You may install optional dependencies:

.. code:: sh

   python3.8 -m pip install "h5RDMtoolbox[mongodb]"  # installs dependencies to use the database mongoDB
   python3.8 -m pip install "h5RDMtoolbox[test]"  # installs dependencies for testing
   python3.8 -m pip install "h5RDMtoolbox[docs]"  # installs dependencies needed to build this documentation
   python3.8 -m pip install "h5RDMtoolbox[complete]"  # installs all above dependencies




.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    Conventions <conventions/index>
    H5wrapper <wrapper/index>
    H5Database <database/index>
    HowTo <howto/howto.ipynb>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

