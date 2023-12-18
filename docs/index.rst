HDF5 Research Data Management Toolbox
=====================================

The "HDF5 Research Data Management Toolbox" (`h5rdmMtoolbox`) is a python package supporting everyone who is working
with HDF5 to achieve a sustainable data lifecycle which follows the
`FAIR <https://www.nature.com/articles/sdata201618>`_ (Findable, Accessible, Interoperable, Reusable) principles.
It specifically supports the five main steps of

 1. Planning (defining a domain- or problem-specific metadata convention and an layout defining the internal structure of HDF5 files)
 2. Collecting data (creating HDF5 files from scratch or converting to HDF5 files from other sources)
 3. :doc:`Analyzing and processing data <wrapper/index>` (Plotting, processing data while keeping the HDF5 attributes by using
    `xarray <https://xarray.pydata.org/>`_)
 4. Sharing data (either into a repository like e.g. `Zenodo <https://zenodo.org>`_ or into a database)
 5. Reusing data (Searching data in databases, local file structures or online repositories
    like `Zenodo <https://zenodo.org>`_).


.. image:: _static/new_icon_with_text.svg
  :width: 500
  :alt: Alternative text
  :align: center


.. note::

   This project is under current development and is happy to receive ideas, code contributions as well as
   `bug and issue reports <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_.
   Thank you!


Overview
--------
The `h5rdmtoolbox` is organized in five sub-packages corresponding to main features, which are needed to achieve a
sustainable data lifecycle. The sub-packages are:

  - :doc:`wrapper <wrapper/index>`: User-friendly wrapper around `h5py` implementation for efficient work with HDF5 files and conventions
  - :doc:`convention <convention/index>`: Simple, user-definable construction of conventions (metadata standardization for HDF files)
  - :doc:`database <database/index>`: Querying HDF5 files (A database for HDF5 files or interfacing with dedicated solutions, like mongoDB)
  - :doc:`repository <repository/index>`: Up/Download to/from repositories (currently, a Zenodo interface is implemented)
  - :doc:`layout <layout/index>`: User-definable specifications for the layout of HDF5 files (attributes, datasets, groups and properties)

Besides the wrapper, which uses the convention sub-package, all sub-packages are independent of each other and can be
developed and used separately.


.. image:: _static/h5tbx_modules.svg
  :width: 500
  :alt: Alternative text
  :align: center

Please navigate through the chapters on the left to learn more about the package. They are organized in the following:

      - :doc:`Getting Started <gettingstarted/index>`: A quick introduction to the package
      - :doc:`Working with HDF5 files <wrapper/index>`: A high-level wrapper for HDF5 files
      - :doc:`Convention <convention/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`Layout <layout/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`Repository <repository/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`Database <database/index>`: A database for HDF5 files
      - :doc:`HowTo and FAQs <howto/index>`: A collection of FAQs
      - :doc:`API Reference <api>`: The API reference
      - :doc:`Glossary <glossary/index>`: A glossary of terms used in the package
      - :doc:`References <references>`: A list of references used in the package

Installation
------------
The repository requires python 3.8. or higher (automatic testing is performed until 3.12).

.. code:: sh

   pip install h5RDMtoolbox

You may want to install optional dependencies:

.. code:: sh

   # install dependencies to use the database mongoDB
   pip install h5RDMtoolbox[mongodb]

   # install dependencies for testing
   pip install h5RDMtoolbox[test]

   # install dependencies needed to build this documentation
   pip install h5RDMtoolbox[docs]

   # install all above dependencies
   pip install h5RDMtoolbox[complete]


.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: Documentation

    Getting Started <gettingstarted/index>
    Working with HDF <wrapper/index>
    Conventions <conventions/index>
    Layout <layout/index>
    Database <database/index>
    Repository <repository/index>
    Practical Examples <practical_examples/index>
    HowTo <howto/index>
    API Reference <api>
    Glossary <glossary/index>
    References <references>

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Repository

   GitHub Repository <https://github.com/matthiasprobst/h5RDMtoolbox>

