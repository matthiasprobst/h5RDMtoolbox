x2hdf: Conversion of specifc data to HDF
========================================


This sub-package `x2hdf` provides conversion methods for various domains. This is needed because not every
third party software allows exporting to the HDF5 format - and even if, it may not be in the required layout
and may not fulfill the conventions required.
In the current version first conversion options are given with piv2hdf (Conversion of Particle Image Velocimetry data)
and cfd2hdf (Conversion of Computational Fluid Dynamics data).


.. toctree::
    :maxdepth: 2
    :hidden:

    piv2hdf.ipynb
    cfx2hdf.ipynb