HDF Research Data Management Toolbox
====================================

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package that provides a set of tools to work
**efficiently** and **sustainably** with HDF5 files. It is intended to help researches in projects achieving
`FAIR <https://www.nature.com/articles/sdata201618>`_ data management based on HDF5 files.

It supports users with
 - :doc:`data creation <wrapper/index>`
 - :doc:`processing <wrapper/index>`
 - :doc:`sharing <database/index>`

In order to achieve sustainable data that can be shared within a project/collaboration or a community standards or
`conventions <conventions/index>` within the respective environment need to be respected, The toolbox provides a tool to integrate meta-data-
standards during the steps of creation, processing and sharing of data.

HDF5 files can be used as a :doc:`database <database/index>` directly or can be integrated in a non-relational database
(mongoDB) with the toolbox. This
allows to identify data based on meta information. Above standards help to identify data and to make it findable.


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
      - :doc:`Create and process Files <wrapper/index>`: A high-level wrapper for HDF5 files
      - :doc:`Conventions <conventions/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`HDF5 Database solutions <database/index>`: A database for HDF5 files
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

