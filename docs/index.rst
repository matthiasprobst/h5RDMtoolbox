HDF Research Data Management Toolbox
====================================

The "HDF5 Research Data Management Toolbox" (h5RDMtoolbox) is a python package supporting everyone who is working
with HDF5 to achieve a sustainable data lifecycle which follows the
`FAIR <https://www.nature.com/articles/sdata201618>`_ (Findable, Accessible, Interoperable, Reusable) principles.
It specifically supports the five main steps of

 1. Planning (defining domain- or problem-specific metadata convention(s) and an internal layout(s) for HDF5 files)
 2. Collecting data (creating HDF5 files from scratch or converting to HDF5 files from other sources)
 3. :doc:`Analyzing and processing data <wrapper/index>` (Plotting, processing data while keeping the HDF5 attributes by using
    `xarray <https://xarray.pydata.org/>`_)
 4. Sharing data (publishing, archiving, ... e.g. to databases like `mongoDB <https://www.mongodb.com/>`_ or repositories
    like `Zenodo <https://zenodo.org>`_
 5. Reusing data (Searching data in databases, local file structures or online repositories
    like `Zenodo <https://zenodo.org>`_.


.. image:: _static/new_icon_with_text.svg
  :width: 500
  :alt: Alternative text
  :align: center


.. note::

   This project is under current development and is happy to receive ideas as well as
   `bug and issue reports <https://github.com/matthiasprobst/h5RDMtoolbox/issues/new?title=Issue%20on%20page%20%2Findex.html&body=Your%20issue%20content%20here.>`_.
   Thank you!


Overview
--------
The packages come with three sub-packages, each covering a different aspect of efficient and sustainable work with
HDF5 files:

  - :doc:`convention <conventions/index>`: Modular construction of conventions (meta data standardization for HDF files)
  - :doc:`wrapper <wrapper/index>`: User-friendly wrapper around `h5py` implementation for efficient work with HDF5 files and above conventions
  - :doc:`database <database/index>`: Querying HDF5 files (A database for HDF5 files or interfacing with mongoDB)


Please navigate through the chapters on the left to learn more about the package. They are organized in the following:

      - :doc:`Getting Started <gettingstarted/index>`: A quick introduction to the package
      - :doc:`Working with HDF5 files <wrapper/index>`: A high-level wrapper for HDF5 files
      - :doc:`Conventions <conventions/index>`: Modular construction of conventions (sets of standardized HDF5 attributes)
      - :doc:`Database <database/index>`: A database for HDF5 files
      - :doc:`HowTo and FAQs <howto/index>`: A collection of FAQs
      - :doc:`API Reference <api>`: The API reference
      - :doc:`Glossary <glossary/index>`: A glossary of terms used in the package
      - :doc:`References <references>`: A list of references used in the package

Installation
------------
The repository requires python 3.8. or higher (tested for 3.8, 3.9, 3.10).

.. code:: sh

   pip install h5RDMtoolbox

You may want install optional dependencies:

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

