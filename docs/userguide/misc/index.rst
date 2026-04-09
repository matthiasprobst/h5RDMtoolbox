Misc
====

Beyond the scope of the sub-packages, there are many utilities and extensions that are helpful but are not part
of the sub-package implementations. This section outlines them.

Utilities (utils)
-----------------

The ``utils`` module has been organized into submodules for better maintainability:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Description
   * - ``utils.file_io``
     - File I/O utilities (get_filesize, checksum, temporary files)
   * - ``utils.download``
     - Download and network utilities (download_file, DownloadFileManager)
   * - ``utils.hdf5``
     - HDF5-specific utilities (has_datasets, has_groups, version groups)
   * - ``utils.string``
     - String utilities (remove_special_chars)
   * - ``utils.docstring``
     - Docstring parsing utilities (DocStringParser, deprecated decorator)

For backward compatibility, all utilities are still available from ``h5rdmtoolbox.utils``:

.. code-block:: python

    from h5rdmtoolbox import utils

    # These are all still available (re-exported from submodules)
    utils.generate_temporary_filename()
    utils.has_datasets(h5_file)
    utils.DownloadFileManager()

.. note::

    The submodule structure was introduced in v2.7.x. The re-exports in
    ``h5rdmtoolbox.utils`` will be removed in v3.0.0. Import from submodules
    for new code.

Key Utilities
~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   h5rdmtoolbox.utils.generate_temporary_filename
   h5rdmtoolbox.utils.has_datasets
   h5rdmtoolbox.utils.has_groups
   h5rdmtoolbox.utils.DownloadFileManager

Identifiers
-----------

Learn about persistent identifiers for datasets.

.. toctree::
    :titlesonly:
    :glob:

    identifiers.ipynb

Extensions
----------

Xarray extensions for unit handling and more.

.. toctree::
    :titlesonly:
    :glob:

    Extensions.ipynb

Visualization
--------------

Tools for visualizing HDF5 data.

.. toctree::
    :titlesonly:
    :glob:

    Visualization.ipynb

Time Handling
-------------

Utilities for working with dates and times.

.. toctree::
    :titlesonly:
    :glob:

    Time.ipynb

User Directories
----------------

Managing user-specific configuration directories.

.. toctree::
    :titlesonly:
    :glob:

    UserDirectories.ipynb

File Properties
---------------

Working with HDF5 file properties.

.. toctree::
    :titlesonly:
    :glob:

    FileProperties.ipynb

SPARQL Queries
--------------

Querying HDF5 metadata with SPARQL.

.. toctree::
    :titlesonly:
    :glob:

    QueryHDFWithSPARQL.ipynb
