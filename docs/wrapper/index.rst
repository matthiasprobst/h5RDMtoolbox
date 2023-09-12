.. _wrapper:

Working with HDF
================

While processing data, auxiliary data is required to understand the context of the data. This includes information
about the data itself (e.g. units, data type, etc.) as well as information about the data generation (e.g. instrument
settings, etc.). This information is often stored in separate files, however, for HDF5 files it is stored in
attributes right next to the data. This is a powerful feature of HDF5 files but the metadata is lost if data
is extracted by standard packages such as `h5py`.

One of the o features of the toolbox is to provide the user with both, the data and the metadata, by returning
`xarray` objects. This is achieved by wrapping the `h5py` package and extending it with a set of classes. The below
figure illustrates the interaction between the HDF5 file and the user.

.. image:: ../_static/hdf_to_xarray_interface.svg
  :width: 700
  :alt: Alternative text
  :align: center

All in all the wrapper classes around the `h5py` package aim to simplify data
generation, processing, and analysis. The following sections will guide you through those steps.

.. note::

   The wrapper-classes extend but don't limit the functionality of the `h5py` package. The syntax is also "`h5py`-like".
   So, users that are familiar to the `h5py` package will find all features, but will be enforced to provide e.g.
   certain attributes to fulfill the requirements of a certain meta convention.


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
    Misc.ipynb
