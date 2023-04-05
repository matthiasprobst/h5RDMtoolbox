.. _wrapper:

|h5wrappericon| Wrapper around `h5py`
=====================================

.. |h5wrappericon| image:: ../_static/icon_h5wrapper.svg
  :width: 30
  :alt:

Motivated by the need for sustainable research data management, the wrapper sub-package aims to simplify data
generation, processing, and analysis using HDF5 files.
It achieves this by providing a class that inherits from the core interface classes of the popular package `h5py`.
Besides new methods and properties, the "wrapper classes" embedding user-defined (conventions)[conventions]. Please
refer :ref:`here<conventions>` for a detailed description of the conventions.
The following sections will guide you through the complete workflow of creating, writing, and reading HDF5 files and
thereby highlight the advantages of the wrapper classes.

.. note::

   The wrapper-classes extend but don't limit the functionality of the `h5py` package. So users that are
   familiar to the `h5py` package will find all features but will be enforced to provide e.g. certain attributes
   to fulfill the requirements of a certain meta convention.


.. toctree::
    :maxdepth: 2
    :hidden:

    CreateFile.ipynb
    DatasetCreation.ipynb
    DatasetSlicing.ipynb
    GroupCreation.ipynb
    DumpFile.ipynb
    NaturalNaming.ipynb
    SpecialIO.ipynb
    Visualization.ipynb
    Extensions.ipynb
