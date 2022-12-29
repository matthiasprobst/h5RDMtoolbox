|h5wrappericon| HDF5-Wrapper
============================

.. |h5wrappericon| image:: ../icons/icon_h5wrapper.svg
  :width: 30
  :alt:

Motivated by sustainable research data management, the sub-package `wrapper` aims to facilitate data generation, processing and anlysing using HDF5 files. This is done by providing a class that is inherited from the core interface class of the widely used 
package `h5py`. On top of the core wrapper implementation class, specialized classes implement conventions that enforce the usage of 
certain attributes and regulate their values.


.. note::

   The wrapper-classes extend but don't limit the functionality of the `h5py` package. So users that are
   familiar to the `h5py` package will find all featues but will be enforced to provide e.g. certain attributes
   to fulfill the requirements of a certain meta convention.

This notebook will guide through the high-level methods and additional features of the core wrapper/interface class.
Specialized classes associated with a convention get a dedicated section (:ref:`wrapper_and_conventions`)


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
    Wrapper & Conventions <wrapper_and_conventions/index>
