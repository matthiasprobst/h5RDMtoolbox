|h5wrappericon| h5wrapper
=========================

.. |h5wrappericon| image:: ../icons/icon_h5wrapper.svg
  :width: 30
  :alt:

Motivated by sustainable research data management, the package `h5wrapper` aims to integrate meta conventions
during the data generation, processing and anlysing process while facilitating and streamlinig the work at the same
time.
This is done using so-called wrapper-classes, which add functionality to the core interface library `h5py`. The
jupyter notebooks walk you through the usage and features.


.. note::

   The wrapper-classes extend but don't limit the functionality of the `h5py` package. So users that are
   familiar to the `h5py` package will find all featues but will be enforced to provide e.g. certain attributes
   to fulfill the requirements of a certain meta convention.


The package `h5wrapper` adds additional functionalities to the core HDF5-interface, which is implemented in the
package `h5py` (https://docs.h5py.org/en/stable/). This is done by providing so-calle wrapper classes. They
  - facilitate and streamline the work with HDF5 files and
  - integrate meta-conventions and file-layout specifications.

Besides high-level methods that enhances the usability, naming `conventions`, the usage of `units` and the defintion of so-called `layouts` are a core feature. They are motivated by the FAIR principles of sustainable data management.

This notebook will guide through the high-level methods and the mentioned concepts.

The package `h5wrapper` provides classes that ar inherited from the interface classes of `h5py`. They are
wrapper-classes as they streamline the work with HDF5 files and provide additional functionality to them.

Wrapper files enhances the usability of HDF5files by

  simplifying the interaction using natural naming, interactive and clean content repesentation and the usage of
  xarray classes instead of numpy arrays

and by

  introduction of metadata conventions such as `standard_names`, `long_names` and layout definitions.

All above enhances the FAIRness (FAIR=Findable+Accessible+Interoperable+re-usable) of HDF5 files.


.. toctree::
    :maxdepth: 2
    :hidden:

    CreateFile.ipynb
    DatasetCreation.ipynb
    DatasetSlicing.ipynb
    GroupCreation.ipynb
    FileExploration.ipynb
    NaturalNaming.ipynb
    Conventions.ipynb
    SpecialIO.ipynb
    Visualization.ipynb
    Extensions.ipynb
    SpecialAttributes.ipynb
    SpecializedWrappers.ipynb

