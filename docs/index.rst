HDF Research Data Management Toolbox
====================================

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package that provides a set of tools to work
with HDF5 files. It is intended to help researches in projects achieving
`FAIR principles <https://www.nature.com/articles/sdata201618>`_ data management based on HDF5 files. It
supports with data creation, processing and sharing.


.. note::

   This project is still beta. Usage is at your own risk. Please report any issues on the `here <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_. Thank you!


Overview
========
The packages comes with three sub-packages, each of it covering a different aspect of efficient and sustained work with
HDF5 files:

  - :doc:`convention <conventions/index>`: Naming standards for specific attributes in the HDF5 files
  - :doc:`wrapper <wrapper/index>`: Efficient high-level objects for efficient work with HDF5 files
  - :doc:`database <database/index>`: Querying HDF5 files

.. image:: _static/package_overview.svg
  :width: 350
  :alt: Alternative text
  :align: center

Installation
------------
The repository requires python 3.8. or higher (tested for 3.8, 3.9, 3.10).

Install from source from github:

.. code:: sh

   python -m pip install https://github.com/matthiasprobst/h5RDMtoolbox

Clone and install from source:

.. code:: sh

   git clone https://github.com/matthiasprobst/h5RDMtoolbox
   python3.8 -m pip install h5RDMtoolbox/

You may install optional dependencies:

.. code:: sh

   # install dependencies to use the database mongoDB
   python3.8 -m pip install "h5RDMtoolbox[mongodb]"

   # install dependencies for testing
   python3.8 -m pip install "h5RDMtoolbox[test]"

   # install dependencies needed to build this documentation
   python3.8 -m pip install "h5RDMtoolbox[docs]"

   # install all above dependencies
   python3.8 -m pip install "h5RDMtoolbox[complete]"


.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    HDF5-Wrapper <wrapper/index>
    HDF5-Database <database/index>
    Conventions <conventions/index>
    HowTo <howto/howto.ipynb>
    API Reference <api>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

