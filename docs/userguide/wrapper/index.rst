.. _wrapper:

Working with HDF
================

While processing data, auxiliary data is required to understand the context of the data. This includes information
about the data itself (e.g. units, data type, etc.) as well as information about the data generation (e.g. instrument
settings, etc.). This information is often stored in separate files, however, for HDF5 files it is stored in
attributes right next to the data. This is a powerful feature of HDF5 files. However, `h5py` only returns the data 
as `numpy` arrays. The attribute data needs to be read separately. Also information about dimension scales is not returned 
to the user.

The `h5rdmtoolbox` makes use of `xarray` objects, which wrap a very similar concept around a `numpy` array, such that 
attributes and coordinates (respective concept to HDF dimension scales) are provided with the dataset values. The below
figure illustrates the principle workflow. Before data is returned to the user, attributes and possibly related dimension 
scale data is retrieved to instantiate a `xarray.DataArray` object, which is returned to the user. With this, not only all 
information is grant to the user, but also very helpful features of the `xarray` library (e.g. plotting) are obtained.  

.. image:: ../../_static/hdf_to_xarray_interface.svg
  :width: 700
  :alt: Alternative text
  :align: center

All in all, the wrapper module aims to provide simple interfaces to HDF5 files to enhance data
generation, processing, and analysis. The following sections will guide you through those steps.

.. note::

   The package extends but does not limit the functionality of the `h5py` package. The syntax is also "`h5py`-like".
   So, users that are familiar to the `h5py` package will find all features.


.. toctree::
    :maxdepth: 2
    :hidden:

    CreateFile.ipynb
    DatasetCreation.ipynb
    FAIRAttributes.ipynb
    DatasetSlicing.ipynb
    GroupCreation.ipynb
    DumpFile.ipynb
    NaturalNaming.ipynb
    SpecialIO.ipynb
