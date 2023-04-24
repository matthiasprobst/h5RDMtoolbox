HDF Research Data Management Toolbox
====================================

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package that provides a set of tools to work
with HDF5 files. It is intended to help researches in projects achieving
`FAIR <https://www.nature.com/articles/sdata201618>`_ data management based on HDF5 files. It
supports users with data creation, processing and sharing. :doc:`Conventions <conventions/index>` can be designed flexible
and to the needs of the respective project or collaboration. They are respected by the interface
(:doc:`wrapper <wrapper/index>`) built around the core package `h5py`. Additionally, the package provides tools to
:doc:`query <database/index>` HDF5 files in a file system or through a database (mongoDB).


.. note::

   This project is still beta. Usage is at your own risk. Please report any issues on the `here <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_. Thank you!


Overview
--------
The packages comes with three sub-packages, each covering a different aspect of efficient and sustainable work with
HDF5 files:

  - :doc:`convention <conventions/index>`: Modular construction of conventions (standardization and specification for HDF files)
  - :doc:`wrapper <wrapper/index>`: User-friendly wrapper around `h5py` implementation for efficient work with HDF5 files and above conventions
  - :doc:`database <database/index>`: Querying HDF5 files (A database for HDF5 files)

.. image:: _static/package_overview.svg
  :width: 350
  :alt: Alternative text
  :align: center

Please navigate through the chapters on the left to learn more about the package. They are organized in the following:

      - :doc:`Getting Started <gettingstarted/index>`: A quick introduction to the package
      - :doc:`Wrapper <wrapper/index>`: A high-level wrapper for HDF5 files
      - :doc:`Conventions <conventions/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`Database <database/index>`: A database for HDF5 files
      - :doc:`HowTo <howto/index>`: A collection of FAQs how to do things
      - :doc:`API Reference <api>`: The API reference
      - :doc:`Glossary <glossary/index>`: A glossary of terms used in the package
      - :doc:`References <references>`: A list of references used in the package

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
    Wrapper <wrapper/index>
    Conventions <conventions/index>
    Database <database/index>
    HowTo <howto/index>
    API Reference <api>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

